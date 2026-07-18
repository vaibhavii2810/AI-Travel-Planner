/**
 * Centralized API client.
 * All HTTP calls go through this module — no fetch/axios scattered in components.
 * Base URL is read from the VITE_API_BASE_URL environment variable.
 */
import axios, { AxiosError } from 'axios';
import type { AxiosInstance } from 'axios';
import type {
  CreatePlanRequest,
  CreatePlanResponse,
  FinalPlanResponse,
  PlanStatusResponse,
  ReviewRequest,
  ReviewResponse,
} from '@/types/api';

// ── Axios instance ────────────────────────────────────────────────────────────

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string) || 'http://localhost:8000';
const API_PREFIX = '/api/v1';

const http: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}${API_PREFIX}`,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
  timeout: 90_000, // 90s — AI planning can take a while
});

// ── Error normalization ───────────────────────────────────────────────────────

export interface ApiError {
  status: number;
  errorCode: string;
  message: string;
  planId?: string;
  raw?: unknown;
}

function toApiError(err: unknown): ApiError {
  if (axios.isAxiosError(err)) {
    const axErr = err as AxiosError<{ error?: string; message?: string; plan_id?: string }>;
    const status = axErr.response?.status ?? 0;
    const data = axErr.response?.data;

    // Map HTTP status codes to friendly messages when backend doesn't supply one
    const fallbackMessages: Record<number, string> = {
      400: 'The request was invalid. Please check your inputs.',
      404: "We couldn't find this travel plan.",
      409: 'This plan has not been approved yet, or the action is not valid in the current state.',
      422: 'Validation error — please check all required fields.',
      500: 'The server encountered an unexpected error. Please try again.',
      503: 'The planning service is temporarily unavailable.',
      0:   'Network error — please check your connection and ensure the backend is running.',
    };

    return {
      status,
      errorCode: data?.error ?? 'API_ERROR',
      message: data?.message ?? fallbackMessages[status] ?? 'An unexpected error occurred.',
      planId: data?.plan_id ?? undefined,
      raw: data,
    };
  }

  if (err instanceof Error) {
    return { status: 0, errorCode: 'NETWORK_ERROR', message: err.message };
  }

  return { status: 0, errorCode: 'UNKNOWN_ERROR', message: 'An unknown error occurred.' };
}

// ── API functions ─────────────────────────────────────────────────────────────

/**
 * POST /plan — Submit a new travel planning request.
 * Returns immediately after LangGraph reaches the HITL interrupt.
 */
export async function createPlan(request: CreatePlanRequest): Promise<CreatePlanResponse> {
  try {
    const { data } = await http.post<CreatePlanResponse>('/plan', request);
    return data;
  } catch (err) {
    throw toApiError(err);
  }
}

/**
 * GET /plan/{plan_id} — Get current plan status and draft itinerary.
 */
export async function getPlan(planId: string): Promise<PlanStatusResponse> {
  try {
    const { data } = await http.get<PlanStatusResponse>(`/plan/${planId}`);
    return data;
  } catch (err) {
    throw toApiError(err);
  }
}

/**
 * POST /plan/{plan_id}/review — Submit HITL review decision.
 * action = 'approve' | 'reject' | 'modify'
 */
export async function reviewPlan(planId: string, review: ReviewRequest): Promise<ReviewResponse> {
  try {
    const { data } = await http.post<ReviewResponse>(`/plan/${planId}/review`, review);
    return data;
  } catch (err) {
    throw toApiError(err);
  }
}

/**
 * GET /plan/{plan_id}/final — Get finalized itinerary (only after approval).
 * Returns 409 if plan is not yet finalized.
 */
export async function getFinalPlan(planId: string): Promise<FinalPlanResponse> {
  try {
    const { data } = await http.get<FinalPlanResponse>(`/plan/${planId}/final`);
    return data;
  } catch (err) {
    throw toApiError(err);
  }
}
