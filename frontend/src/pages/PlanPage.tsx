import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, CheckCircle, Printer, Copy } from 'lucide-react';
import { WorkflowStepper } from '@/components/WorkflowStepper';
import { PlanSummary } from '@/components/PlanSummary';
import { ItineraryTimeline } from '@/components/ItineraryTimeline';
import { BudgetSummary } from '@/components/BudgetSummary';
import { ReviewActions } from '@/components/ReviewActions';
import { ApproveDialog } from '@/components/ApproveDialog';
import { RejectModal } from '@/components/RejectModal';
import { ModifyModal } from '@/components/ModifyModal';
import { ErrorState } from '@/components/ui/ErrorState';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { ItinerarySkeleton, PlanSummarySkeleton } from '@/components/ui/LoadingSkeleton';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { usePlan } from '@/hooks/usePlan';

// Status messages shown during AI processing phases
const STATUS_MESSAGES: Record<string, { heading: string; sub: string }> = {
  queued:      { heading: 'Your request is queued…',               sub: 'The AI agents are starting up.' },
  researching: { heading: 'Researching your destination…',         sub: 'Gathering real-time insights, attractions, and weather data.' },
  planning:    { heading: 'Building your personalized itinerary…', sub: 'The planner is crafting your day-by-day plan.' },
  revising:    { heading: 'Applying your feedback…',               sub: 'The AI is revising your itinerary based on your input.' },
};

export function PlanPage() {
  const { planId } = useParams<{ planId: string }>();
  const navigate = useNavigate();

  const { plan, finalPlan, loading, reviewLoading, error, refetch, submitReview } = usePlan(planId);

  // Modal state
  const [showApprove, setShowApprove] = useState(false);
  const [showReject, setShowReject]   = useState(false);
  const [showModify, setShowModify]   = useState(false);
  const [copied, setCopied]           = useState(false);

  // Initial fetch on mount (and store plan_id for refresh recovery)
  useEffect(() => {
    if (planId) {
      if (planId) localStorage.setItem('activePlanId', planId);
      refetch();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [planId]);

  // ── Review handlers ────────────────────────────────────────────────────────

  const handleApproveConfirm = async () => {
    await submitReview({ action: 'approve' });
    setShowApprove(false);
  };

  const handleRejectSubmit = async (feedback: string) => {
    await submitReview({ action: 'reject', feedback });
    setShowReject(false);
  };

  const handleModifySubmit = async (instructions: string) => {
    await submitReview({
      action: 'modify',
      modifications: { instructions },
    });
    setShowModify(false);
  };

  // ── Copy plan ID ───────────────────────────────────────────────────────────

  const copyPlanId = async () => {
    if (!planId) return;
    try {
      await navigator.clipboard.writeText(planId);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Silently ignore clipboard errors
    }
  };

  // ── Render states ──────────────────────────────────────────────────────────

  // Initial load
  if (loading && !plan) {
    return (
      <PageShell planId={planId}>
        <PlanSummarySkeleton />
        <div className="mt-6">
          <ItinerarySkeleton />
        </div>
      </PageShell>
    );
  }

  // Error
  if (error && !plan) {
    return (
      <PageShell planId={planId}>
        <ErrorState error={error} onRetry={refetch} />
      </PageShell>
    );
  }

  if (!plan) return null;

  const itinerary = plan.draft_itinerary ?? plan.final_itinerary;
  const currency  = plan.travel_request?.budget_currency ?? 'USD';
  const isProcessing = ['queued', 'researching', 'planning', 'revising'].includes(plan.status);
  const isAwaitingReview = plan.status === 'awaiting_review';
  const isFinalized      = plan.status === 'finalized';
  const isError          = plan.status === 'error' || plan.status === 'max_revisions_exceeded';

  const displayItinerary = isFinalized ? (finalPlan?.final_itinerary ?? itinerary) : itinerary;

  return (
    <>
      <PageShell planId={planId} onCopyId={copyPlanId} copied={copied}>
        {/* Workflow stepper */}
        <div className="bg-white rounded-2xl border border-slate-100 shadow-card px-6 py-5 mb-6">
          <WorkflowStepper status={plan.status} />
        </div>

        {/* AI processing state */}
        {isProcessing && (
          <div className="bg-white rounded-2xl border border-brand-100 shadow-card p-8 mb-6 flex flex-col items-center text-center animate-fade-in">
            <LoadingSpinner size="lg" className="text-brand-500 mb-4" />
            <h2 className="text-lg font-bold text-slate-900 mb-1">
              {STATUS_MESSAGES[plan.status]?.heading ?? 'Processing…'}
            </h2>
            <p className="text-sm text-slate-500 max-w-sm">
              {STATUS_MESSAGES[plan.status]?.sub ?? 'Please wait while the AI works on your plan.'}
            </p>
            <div className="mt-4">
              <StatusBadge status={plan.status} />
            </div>
          </div>
        )}

        {/* Error state from backend */}
        {isError && (
          <div className="bg-red-50 border border-red-200 rounded-2xl p-6 mb-6 animate-fade-in">
            <h2 className="text-lg font-bold text-red-700 mb-1">
              {plan.status === 'max_revisions_exceeded' ? 'Maximum Revisions Reached' : 'Planning Error'}
            </h2>
            <p className="text-sm text-red-600 mb-4">
              {plan.error_message ??
                (plan.status === 'max_revisions_exceeded'
                  ? 'The plan has exceeded the maximum number of revisions. Please start a new plan.'
                  : 'An error occurred during planning. Please try again.')}
            </p>
            <Link
              to="/new"
              className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white text-sm font-semibold rounded-xl hover:bg-red-700 transition-colors"
            >
              Start a new plan
            </Link>
          </div>
        )}

        {/* Plan summary — always show when plan data available */}
        {plan && <div className="mb-6"><PlanSummary plan={plan} /></div>}

        {/* HITL Review panel */}
        {isAwaitingReview && (
          <div className="mb-6">
            <ReviewActions
              loading={reviewLoading}
              onApprove={() => setShowApprove(true)}
              onReject={() => setShowReject(true)}
              onModify={() => setShowModify(true)}
              revisionCount={plan.revision_count}
            />
          </div>
        )}

        {/* Finalized success banner */}
        {isFinalized && (
          <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-6 mb-6 flex flex-col sm:flex-row items-start sm:items-center gap-4 animate-slide-up">
            <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center flex-shrink-0">
              <CheckCircle className="w-5 h-5 text-emerald-600" aria-hidden="true" />
            </div>
            <div className="flex-1">
              <h2 className="text-base font-bold text-emerald-900">Your Trip Is Ready! 🎉</h2>
              <p className="text-sm text-emerald-700 mt-0.5">
                Your itinerary has been approved and finalized. Have a wonderful trip!
              </p>
            </div>
            <button
              onClick={() => window.print()}
              className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white text-sm font-semibold rounded-xl hover:bg-emerald-700 transition-colors focus:outline-none focus:ring-2 focus:ring-emerald-500"
              aria-label="Print itinerary"
            >
              <Printer className="w-4 h-4" aria-hidden="true" />
              Print
            </button>
          </div>
        )}

        {/* Draft / Final itinerary */}
        {displayItinerary && (
          <>
            {isAwaitingReview && plan.revision_count > 0 && (
              <div className="mb-4 px-4 py-2 bg-amber-50 border border-amber-100 rounded-xl text-sm text-amber-700 font-medium animate-fade-in">
                📝 Revised Plan — Awaiting Your Review (Revision {plan.revision_count})
              </div>
            )}

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
              {/* Itinerary timeline — main column */}
              <div className="xl:col-span-2">
                <h3 className="text-base font-bold text-slate-700 uppercase tracking-wide mb-4">
                  {isFinalized ? 'Final Itinerary' : 'Draft Itinerary'} · v{displayItinerary.version}
                </h3>
                {loading ? (
                  <ItinerarySkeleton />
                ) : (
                  <ItineraryTimeline itinerary={displayItinerary} currency={currency} />
                )}
              </div>

              {/* Budget sidebar */}
              <div className="xl:col-span-1">
                <h3 className="text-base font-bold text-slate-700 uppercase tracking-wide mb-4">
                  Budget
                </h3>
                <BudgetSummary
                  budget={displayItinerary.budget_allocation}
                  budgetMax={plan.travel_request?.budget_max}
                />
              </div>
            </div>
          </>
        )}

        {/* Loading skeleton while initial itinerary is being generated */}
        {isProcessing && !displayItinerary && (
          <div className="mt-6">
            <ItinerarySkeleton />
          </div>
        )}

        {/* API error toast — shown when a review action fails but plan is still visible */}
        {error && plan && (
          <div className="fixed bottom-4 right-4 max-w-sm bg-red-50 border border-red-200 rounded-xl shadow-lg p-4 text-sm text-red-700 animate-slide-up" role="alert">
            <span className="font-semibold">Action failed: </span>
            {typeof error === 'string' ? error : error.message}
          </div>
        )}
      </PageShell>

      {/* Modals */}
      <ApproveDialog
        open={showApprove}
        loading={reviewLoading}
        onConfirm={handleApproveConfirm}
        onCancel={() => setShowApprove(false)}
      />
      <RejectModal
        open={showReject}
        loading={reviewLoading}
        onSubmit={handleRejectSubmit}
        onClose={() => setShowReject(false)}
      />
      <ModifyModal
        open={showModify}
        loading={reviewLoading}
        onSubmit={handleModifySubmit}
        onClose={() => setShowModify(false)}
      />
    </>
  );
}

// ── PageShell ──────────────────────────────────────────────────────────────────

interface PageShellProps {
  planId?: string;
  onCopyId?: () => void;
  copied?: boolean;
  children: React.ReactNode;
}

function PageShell({ planId, onCopyId, copied, children }: PageShellProps) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-brand-50">
      {/* Header */}
      <header className="border-b border-slate-100 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <Link
              to="/new"
              className="flex items-center gap-1.5 text-slate-500 hover:text-slate-800 transition-colors text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 rounded-lg px-1"
              aria-label="Back to home"
            >
              <ArrowLeft className="w-4 h-4" aria-hidden="true" />
              <span className="hidden sm:inline">New Plan</span>
            </Link>
            <div className="w-px h-5 bg-slate-200" aria-hidden="true" />
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-lg bg-brand-600 flex items-center justify-center">
                <span className="text-white text-xs" aria-hidden="true">✈️</span>
              </div>
              <span className="font-bold text-slate-900 text-sm sm:text-base">AI Travel Planner</span>
            </div>
          </div>

          {planId && onCopyId && (
            <button
              onClick={onCopyId}
              className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-600 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 rounded-lg px-2 py-1"
              aria-label="Copy plan ID"
            >
              <Copy className="w-3.5 h-3.5" aria-hidden="true" />
              <span className="font-mono hidden sm:inline">{planId.slice(0, 12)}…</span>
              {copied && <span className="text-emerald-500 ml-1">Copied!</span>}
            </button>
          )}
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        {children}
      </main>
    </div>
  );
}
