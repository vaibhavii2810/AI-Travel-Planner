/**
 * usePlan — central state hook for the plan workflow.
 *
 * Responsibilities:
 * - Fetch plan state from GET /plan/{plan_id}
 * - Poll while status is in an active-processing state
 * - Expose review handlers (approve/reject/modify)
 * - Fetch final plan after approval
 */
import { useCallback, useState, useRef } from 'react';
import { usePolling } from './usePolling';
import {
  getPlan,
  reviewPlan,
  getFinalPlan,
  type ApiError,
} from '@/api/client';
import type {
  FinalPlanResponse,
  PlanStatus,
  PlanStatusResponse,
  ReviewRequest,
} from '@/types/api';

// Statuses where we should poll for updates
const POLLING_STATUSES: PlanStatus[] = ['queued', 'researching', 'planning', 'revising'];
const POLL_INTERVAL_MS = 2500;

export interface UsePlanReturn {
  plan: PlanStatusResponse | null;
  finalPlan: FinalPlanResponse | null;
  loading: boolean;
  reviewLoading: boolean;
  error: ApiError | null;
  refetch: () => Promise<void>;
  submitReview: (review: ReviewRequest) => Promise<void>;
}

export function usePlan(planId: string | undefined): UsePlanReturn {
  const [plan, setPlan] = useState<PlanStatusResponse | null>(null);
  const [finalPlan, setFinalPlan] = useState<FinalPlanResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  // Keep a ref to current plan so polling closure always sees latest value
  const planRef = useRef<PlanStatusResponse | null>(null);
  planRef.current = plan;

  const fetchPlan = useCallback(async () => {
    if (!planId) return;
    try {
      const data = await getPlan(planId);
      setPlan(data);
      setError(null);

      // If finalized, also fetch the final plan
      if (data.status === 'finalized' && !planRef.current?.final_itinerary) {
        try {
          const fp = await getFinalPlan(planId);
          setFinalPlan(fp);
        } catch {
          // Non-fatal: plan might briefly show finalized before final endpoint is ready
        }
      }
    } catch (err) {
      setError(err as ApiError);
    }
  }, [planId]);

  // Initial fetch + set loading on first call
  const refetch = useCallback(async () => {
    if (!planId) return;
    setLoading(true);
    await fetchPlan();
    setLoading(false);
  }, [planId, fetchPlan]);

  // Poll whenever plan is in an active processing state
  const shouldPoll = !!planId && !!plan && POLLING_STATUSES.includes(plan.status);
  usePolling(fetchPlan, POLL_INTERVAL_MS, shouldPoll);

  const submitReview = useCallback(
    async (review: ReviewRequest) => {
      if (!planId) return;
      setReviewLoading(true);
      setError(null);
      try {
        await reviewPlan(planId, review);

        // Immediately refetch to capture any fast status transition
        const updated = await getPlan(planId);
        setPlan(updated);

        // If immediately finalized (approve path), fetch the final itinerary
        if (updated.status === 'finalized') {
          try {
            const fp = await getFinalPlan(planId);
            setFinalPlan(fp);
          } catch {
            // Will be retried on next poll cycle
          }
        }
        // For reject/modify paths the status will be 'revising' — polling
        // (shouldPoll becomes true again) takes over from here automatically.
      } catch (err) {
        setError(err as ApiError);
      } finally {
        setReviewLoading(false);
      }
    },
    [planId],
  );

  return { plan, finalPlan, loading, reviewLoading, error, refetch, submitReview };
}
