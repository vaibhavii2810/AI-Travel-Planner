/**
 * TypeScript interfaces that exactly mirror the FastAPI/Pydantic backend schemas.
 * Do not add computed fields or invent structures not present in the API.
 */

// ── Request Types ─────────────────────────────────────────────────────────────

export interface CreatePlanRequest {
  destination: string;
  start_date: string;      // ISO date string "YYYY-MM-DD"
  end_date: string;        // ISO date string "YYYY-MM-DD"
  budget_min: number;
  budget_max: number;
  budget_currency: string; // default "USD"
  interests: string[];
  num_travelers: number;
}

export type ReviewAction = 'approve' | 'reject' | 'modify';

export interface ReviewRequest {
  action: ReviewAction;
  feedback?: string | null;         // required when action === 'reject'
  modifications?: Record<string, unknown> | null; // required when action === 'modify'
}

// ── Domain Types ──────────────────────────────────────────────────────────────

export interface Activity {
  name: string;
  description: string;
  location: string;
  duration_minutes: number;
  estimated_cost_per_person: number;
  booking_required: boolean;
  tips: string;
}

export interface DailyPlan {
  day_number: number;
  date: string;          // ISO date or date string from backend
  theme: string;
  morning: Activity[];
  afternoon: Activity[];
  evening: Activity[];
  accommodation: string;
  estimated_daily_cost_per_person: number;
  practical_notes: string; // aliased as travel_notes in backend response
}

export interface BudgetAllocation {
  accommodation_total: number;
  transport_total: number;
  food_total: number;
  activities_total: number;
  contingency_total: number;
  grand_total: number;
  per_person_total: number;
  currency: string;
  within_budget: boolean;
  notes: string;
}

export interface DraftItinerary {
  version: number;
  daily_plans: DailyPlan[];
  budget_allocation: BudgetAllocation;
  overall_tips: string[];
  packing_suggestions: string[];
  generated_at: string; // ISO datetime
}

export interface WeatherSummary {
  avg_temp_celsius: number;
  avg_temp_fahrenheit: number;
  conditions: string;
  precipitation_chance_percent: number;
  humidity_percent: number;
  warnings: string[];
  data_available: boolean;
}

export interface Attraction {
  name: string;
  description: string;
  category: string;
  estimated_visit_duration_hours: number;
  approximate_cost_per_person: number;
}

export interface ResearchOutput {
  attractions: Attraction[];
  local_tips: string[];
  safety_considerations: string[];
  weather_summary: WeatherSummary;
  seasonal_notes: string;
  general_destination_info: string;
  research_sources: string[];
  researched_at: string; // ISO datetime
}

export interface TravelRequest {
  destination: string;
  start_date: string;
  end_date: string;
  budget_min: number;
  budget_max: number;
  budget_currency: string;
  interests: string[];
  num_travelers: number;
}

// ── Status Values — matches backend constants exactly ─────────────────────────

export type PlanStatus =
  | 'queued'
  | 'researching'
  | 'planning'
  | 'awaiting_review'
  | 'revising'
  | 'finalizing'
  | 'finalized'
  | 'error'
  | 'max_revisions_exceeded'
  | 'rejected';

// ── Response Types ────────────────────────────────────────────────────────────

export interface CreatePlanResponse {
  plan_id: string;
  status: string;
  message: string;
  created_at: string; // ISO datetime
}

export interface PlanStatusResponse {
  plan_id: string;
  status: PlanStatus;
  revision_count: number;
  travel_request?: TravelRequest | null;
  research_summary?: ResearchOutput | null;
  draft_itinerary?: DraftItinerary | null;
  final_itinerary?: DraftItinerary | null;
  error_message?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ReviewResponse {
  plan_id: string;
  status: string;
  action_received: string;
  message: string;
}

export interface FinalPlanResponse {
  plan_id: string;
  status: string;
  final_itinerary: DraftItinerary;
  approved_at?: string | null;
}

export interface ErrorResponse {
  error: string;
  message: string;
  plan_id?: string | null;
}

export interface HealthResponse {
  status: string;
  app_name: string;
  version: string;
  environment: string;
  checkpointer: string;
}
