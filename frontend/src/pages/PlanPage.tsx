import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { CheckCircle, Printer, Copy } from 'lucide-react';
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
import { Navbar } from '@/components/Navbar';
import { usePlan } from '@/hooks/usePlan';

const STATUS_MESSAGES: Record<string, { heading: string; sub: string; icon: string }> = {
  queued:      { heading: 'Request queued…',                   sub: 'The AI agents are spinning up.',                        icon: '⏳' },
  researching: { heading: 'Researching your destination…',     sub: 'Gathering live insights, attractions & weather data.',   icon: '🔍' },
  planning:    { heading: 'Building your itinerary…',          sub: 'The planner is crafting your personalised day-by-day plan.', icon: '🗺️' },
  revising:    { heading: 'Applying your feedback…',           sub: 'Our AI is revising based on what you told us.',         icon: '✍️' },
};

export function PlanPage() {
  const { planId } = useParams<{ planId: string }>();
  const { plan, finalPlan, loading, reviewLoading, error, refetch, submitReview } = usePlan(planId);

  const [showApprove, setShowApprove] = useState(false);
  const [showReject,  setShowReject]  = useState(false);
  const [showModify,  setShowModify]  = useState(false);
  const [copied,      setCopied]      = useState(false);
  const [toastMsg,    setToastMsg]    = useState('');

  useEffect(() => {
    if (planId) {
      localStorage.setItem('activePlanId', planId);
      refetch();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [planId]);

  const handleApproveConfirm = async () => {
    await submitReview({ action: 'approve' });
    setShowApprove(false);
  };
  const handleRejectSubmit = async (feedback: string) => {
    await submitReview({ action: 'reject', feedback });
    setShowReject(false);
    setToastMsg('Feedback sent! The AI agents are researching your revisions.');
    setTimeout(() => setToastMsg(''), 4000);
  };
  const handleModifySubmit = async (instructions: string) => {
    await submitReview({ action: 'modify', modifications: { instructions } });
    setShowModify(false);
    setToastMsg('Modifications submitted! The planner is updating your itinerary.');
    setTimeout(() => setToastMsg(''), 4000);
  };

  const copyPlanId = async () => {
    if (!planId) return;
    try {
      await navigator.clipboard.writeText(planId);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* ignore */ }
  };

  // ── States ─────────────────────────────────────────────────────────────────
  if (loading && !plan) {
    return (
      <Shell planId={planId}>
        <PlanSummarySkeleton />
        <div style={{ marginTop: '24px' }}><ItinerarySkeleton /></div>
      </Shell>
    );
  }

  if (error && !plan) {
    return <Shell planId={planId}><ErrorState error={error} onRetry={refetch} /></Shell>;
  }

  if (!plan) return null;

  const itinerary       = plan.draft_itinerary ?? plan.final_itinerary;
  const currency        = plan.travel_request?.budget_currency ?? 'USD';
  const isRevising       = plan.status === 'revising';
  const isProcessing    = ['queued', 'researching', 'planning', 'revising'].includes(plan.status);
  const isAwaitingReview = plan.status === 'awaiting_review';
  const isFinalized      = plan.status === 'finalized';
  const isError          = plan.status === 'error' || plan.status === 'max_revisions_exceeded' || plan.status === 'rejected';
  // While revising, keep showing old itinerary as a ghost behind the loading overlay
  const displayItinerary = isFinalized ? (finalPlan?.final_itinerary ?? itinerary) : itinerary;

  const statusMsg = STATUS_MESSAGES[plan.status];

  return (
    <>
      <Shell planId={planId} onCopyId={copyPlanId} copied={copied}>

        {/* Workflow stepper */}
        <div style={{
          background: 'var(--bg-card)', border: '1px solid var(--border)',
          borderRadius: '16px', padding: '20px 24px', marginBottom: '20px',
        }}>
          <WorkflowStepper status={plan.status} />
        </div>

        {/* Processing / Revising state — full-page loading panel */}
        {isProcessing && (
          <div style={{
            background: 'var(--bg-card)', border: '1px solid var(--accent-border)',
            borderRadius: '16px', padding: '60px 24px',
            marginBottom: '20px', textAlign: 'center',
          }} className="animate-fade-in">
            <div style={{ fontSize: '44px', marginBottom: '20px' }}>
              {statusMsg?.icon ?? '⚙️'}
            </div>
            <LoadingSpinner size="md" style={{ color: 'var(--accent)', margin: '0 auto 20px' }} />
            <h2 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '8px' }}>
              {statusMsg?.heading ?? 'Processing…'}
            </h2>
            <p style={{ fontSize: '14px', color: 'var(--text-secondary)', maxWidth: '440px', margin: '0 auto 0' }}>
              {statusMsg?.sub ?? 'Please wait.'}
            </p>
            {isRevising && (
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '12px' }}>
                This usually takes 5–15 seconds. The updated plan will appear automatically.
              </p>
            )}
          </div>
        )}

        {/* Backend error or Rejected */}
        {isError && (
          <div style={{
            background: 'rgba(248,113,113,0.06)', border: '1px solid rgba(248,113,113,0.25)',
            borderRadius: '16px', padding: '24px', marginBottom: '20px',
          }} className="animate-fade-in">
            <h2 style={{ fontWeight: 700, color: '#f87171', marginBottom: '6px', fontSize: '16px' }}>
              {plan.status === 'max_revisions_exceeded' 
                ? 'Max Revisions Reached' 
                : plan.status === 'rejected'
                  ? 'Planning Session Rejected'
                  : 'Planning Error'}
            </h2>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
              {plan.status === 'rejected'
                ? 'This travel plan has been rejected and closed. Please start a new planning session.'
                : (plan.error_message ?? 'An error occurred during planning. Please start a new plan.')}
            </p>
            <Link to="/new" className="btn btn-danger" style={{ textDecoration: 'none', display: 'inline-flex' }}>
              Start new plan
            </Link>
          </div>
        )}

        {/* Plan summary */}
        {plan && <div style={{ marginBottom: '20px' }}><PlanSummary plan={plan} /></div>}

        {/* HITL Review panel — only shown when truly awaiting review, not while revising */}
        {isAwaitingReview && !isRevising && (
          <div style={{ marginBottom: '20px' }}>
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
          <div style={{
            background: 'linear-gradient(135deg, rgba(34,197,94,0.12) 0%, rgba(34,197,94,0.04) 100%)',
            border: '1px solid var(--accent-border)',
            borderRadius: '16px',
            padding: '20px 24px',
            marginBottom: '20px',
            display: 'flex',
            alignItems: 'center',
            gap: '16px',
          }} className="animate-slide-up">
            <div style={{
              width: '44px', height: '44px', borderRadius: '50%',
              background: 'rgba(34,197,94,0.15)',
              border: '2px solid var(--accent)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0,
              animation: 'pulse-ring 2s ease-in-out infinite',
            }}>
              <CheckCircle size={20} color="var(--accent)" />
            </div>
            <div style={{ flex: 1 }}>
              <h2 style={{ fontWeight: 700, fontSize: '16px', color: 'var(--text-primary)', marginBottom: '3px' }}>
                Your trip is ready! 🎉
              </h2>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                Your itinerary has been approved and finalised. Pack your bags!
              </p>
            </div>
            <button
              onClick={() => window.print()}
              className="btn btn-primary no-print"
              style={{ flexShrink: 0 }}
            >
              <Printer size={14} /> Print
            </button>
          </div>
        )}



        {/* Itinerary + budget — hidden while revising so the loading screen has full focus */}
        {displayItinerary && !isRevising && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: '24px', alignItems: 'start' }}>
            <div>
              <p style={{
                fontSize: '11px', fontWeight: 700, letterSpacing: '0.08em',
                textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '16px',
              }}>
                {isFinalized ? 'Final Itinerary' : 'Draft Itinerary'} · v{displayItinerary.version}
              </p>
              {loading ? <ItinerarySkeleton /> : (
                <ItineraryTimeline itinerary={displayItinerary} currency={currency} />
              )}
            </div>
            <div>
              <p style={{
                fontSize: '11px', fontWeight: 700, letterSpacing: '0.08em',
                textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '16px',
              }}>
                Budget Breakdown
              </p>
              <BudgetSummary
                budget={displayItinerary.budget_allocation}
                budgetMax={plan.travel_request?.budget_max}
              />
            </div>
          </div>
        )}

        {/* Loading skeleton during processing */}
        {isProcessing && !displayItinerary && (
          <div style={{ marginTop: '24px' }}><ItinerarySkeleton /></div>
        )}

        {/* Success toast — perfectly centered via position + translate */}
        {toastMsg && (
          <div style={{
            position: 'fixed', bottom: '32px',
            left: '50%', transform: 'translateX(-50%)',
            padding: '13px 22px', zIndex: 9999,
            background: 'var(--accent)',
            borderRadius: '99px', boxShadow: '0 4px 28px rgba(34,197,94,0.4)',
            fontSize: '14px', fontWeight: 700, color: '#000',
            display: 'inline-flex', alignItems: 'center', gap: '8px',
            whiteSpace: 'nowrap', userSelect: 'none',
          }} className="animate-slide-up" role="alert">
            <CheckCircle size={16} />
            {toastMsg}
          </div>
        )}

        {/* Error toast */}
        {error && plan && (
          <div style={{
            position: 'fixed', bottom: '20px', right: '20px',
            maxWidth: '360px', padding: '14px 18px',
            background: 'var(--bg-card)', border: '1px solid rgba(248,113,113,0.3)',
            borderRadius: '12px', boxShadow: 'var(--shadow-modal)',
            fontSize: '13px', color: '#f87171',
          }} className="animate-slide-up" role="alert">
            <span style={{ fontWeight: 600 }}>Action failed: </span>
            {typeof error === 'string' ? error : (error as Error).message}
          </div>
        )}
      </Shell>

      {/* Modals */}
      <ApproveDialog open={showApprove} loading={reviewLoading} onConfirm={handleApproveConfirm} onCancel={() => setShowApprove(false)} />
      <RejectModal  open={showReject}  loading={reviewLoading} onSubmit={handleRejectSubmit}    onClose={() => setShowReject(false)} />
      <ModifyModal  open={showModify}  loading={reviewLoading} onSubmit={handleModifySubmit}    onClose={() => setShowModify(false)} />
    </>
  );
}

// ── PageShell ──────────────────────────────────────────────────────────────────
interface ShellProps { planId?: string; onCopyId?: () => void; copied?: boolean; children: React.ReactNode }

function Shell({ planId, onCopyId, copied, children }: ShellProps) {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)' }}>
      <Navbar showBack planId={planId} onCopyId={onCopyId} copied={copied} />
      <main style={{ maxWidth: '1200px', margin: '0 auto', padding: '28px 24px 80px' }}>
        {children}
      </main>
    </div>
  );
}
