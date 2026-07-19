/**
 * usePlan — central state hook for the plan workflow.
 *
 * KEY FIX: After reject/modify, we immediately force local status to 'revising'
 * so the UI shows the loading screen right away, polling continues, and the
 * revised plan appears automatically when the backend finishes.
 */
import { useCallback, useState, useRef, useEffect } from 'react';
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

// Statuses where we should keep polling for updates
const POLLING_STATUSES: PlanStatus[] = ['queued', 'researching', 'planning', 'revising'];
const POLL_INTERVAL_MS = 2000;

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

  // Track whether we should keep polling — stored in a ref so interval always reads latest
  const shouldPollRef = useRef(false);
  const planRef = useRef<PlanStatusResponse | null>(null);
  planRef.current = plan;

  const fetchPlan = useCallback(async () => {
    if (!planId) return;
    try {
      const data = await getPlan(planId);
      setPlan(data);
      setError(null);

      // If finalized, fetch the final itinerary too
      if (data.status === 'finalized') {
        shouldPollRef.current = false;
        try {
          const fp = await getFinalPlan(planId);
          setFinalPlan(fp);
        } catch {
          // Non-fatal — will retry on next poll
        }
      }

      // Stop polling on terminal statuses. 'rejected' is intentionally absent —
      // reject routes through the Orchestrator like modify and comes back as
      // 'awaiting_review', it never terminates the session.
      if (['finalized', 'error', 'max_revisions_exceeded'].includes(data.status)) {
        shouldPollRef.current = false;
      }
    } catch (err) {
      const apiErr = err as ApiError;
      // Plan no longer exists (e.g. dev backend restarted and lost its
      // in-memory store) — the stale id in localStorage would otherwise
      // redirect every future visit to "/" straight into this same error.
      if (apiErr.status === 404) {
        localStorage.removeItem('activePlanId');
      }
      setError(apiErr);
    }
  }, [planId]);

  // Initial fetch + loading indicator
  const refetch = useCallback(async () => {
    if (!planId) return;
    setLoading(true);
    await fetchPlan();
    setLoading(false);
  }, [planId, fetchPlan]);

  // ── Polling engine ────────────────────────────────────────────────────────
  // We manage the interval manually via a ref so we can start/stop it
  // dynamically without relying on React's re-render cycle.
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startPolling = useCallback(() => {
    if (intervalRef.current) return; // already running
    shouldPollRef.current = true;
    intervalRef.current = setInterval(async () => {
      if (!shouldPollRef.current) {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
        return;
      }
      await fetchPlan();
    }, POLL_INTERVAL_MS);
  }, [fetchPlan]);

  const stopPolling = useCallback(() => {
    shouldPollRef.current = false;
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  // Auto-start polling when plan enters a processing status
  useEffect(() => {
    if (!plan) return;
    if (POLLING_STATUSES.includes(plan.status)) {
      startPolling();
    } else {
      stopPolling();
    }
  }, [plan?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  // Cleanup on unmount
  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  // ── Review submission ─────────────────────────────────────────────────────
  const submitReview = useCallback(
    async (review: ReviewRequest) => {
      if (!planId) return;
      setReviewLoading(true);
      setError(null);
      try {
        // CRITICAL FIX: Immediately force status to 'revising' in local state
        // so the loading screen appears right now without waiting for backend.
        if (review.action === 'reject' || review.action === 'modify') {
          setPlan(prev => prev ? { ...prev, status: 'revising' as PlanStatus } : prev);
          // Start polling right away — don't wait for React re-render
          shouldPollRef.current = true;
          startPolling();
        }

        // Submit review to backend
        await reviewPlan(planId, review);

        if (review.action === 'approve') {
          // For approve, fetch immediately and get final plan
          const updated = await getPlan(planId);
          setPlan(updated);
          if (updated.status === 'finalized') {
            try {
              const fp = await getFinalPlan(planId);
              setFinalPlan(fp);
            } catch {
              // Will retry on next poll
            }
          } else {
            startPolling();
          }
        }
        // For reject/modify: polling is already running — it will detect
        // the new 'awaiting_review' status and update the UI automatically.

      } catch (err) {
        setError(err as ApiError);
        // On error, restore previous state from backend
        await fetchPlan();
        stopPolling();
      } finally {
        setReviewLoading(false);
      }
    },
    [planId, fetchPlan, startPolling, stopPolling],
  );

  return { plan, finalPlan, loading, reviewLoading, error, refetch, submitReview };
}
