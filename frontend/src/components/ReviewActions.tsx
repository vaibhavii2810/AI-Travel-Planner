import { CheckCircle, XCircle, Edit3 } from 'lucide-react';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

interface ReviewActionsProps {
  loading: boolean;
  onApprove: () => void;
  onReject: () => void;
  onModify: () => void;
  revisionCount?: number;
}

export function ReviewActions({
  loading,
  onApprove,
  onReject,
  onModify,
  revisionCount = 0,
}: ReviewActionsProps) {
  return (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-card p-6 animate-slide-up">
      {/* Header */}
      <div className="text-center mb-6">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-amber-50 mb-3">
          <span className="text-2xl" aria-hidden="true">✈️</span>
        </div>
        <h2 className="text-lg font-bold text-slate-900">Review Your AI-Generated Trip</h2>
        <p className="text-sm text-slate-500 mt-1">
          Your personalized itinerary is ready.{' '}
          {revisionCount > 0 && (
            <span className="text-brand-600 font-medium">
              Revision {revisionCount} — 
            </span>
          )}
          {' '}What would you like to do?
        </p>
      </div>

      {/* Action buttons */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {/* Approve */}
        <button
          id="approve-plan-btn"
          onClick={onApprove}
          disabled={loading}
          className="flex flex-col items-center gap-2 px-4 py-4 rounded-xl bg-emerald-600 text-white font-semibold hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2"
          aria-label="Approve plan and finalize itinerary"
        >
          {loading ? (
            <LoadingSpinner size="sm" className="text-white" />
          ) : (
            <CheckCircle className="w-6 h-6" aria-hidden="true" />
          )}
          <span className="text-sm">Approve Plan</span>
        </button>

        {/* Reject */}
        <button
          id="reject-plan-btn"
          onClick={onReject}
          disabled={loading}
          className="flex flex-col items-center gap-2 px-4 py-4 rounded-xl border-2 border-red-200 text-red-600 font-semibold hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors focus:outline-none focus:ring-2 focus:ring-red-400 focus:ring-offset-2"
          aria-label="Reject plan and provide feedback for revision"
        >
          <XCircle className="w-6 h-6" aria-hidden="true" />
          <span className="text-sm">Reject & Revise</span>
        </button>

        {/* Modify */}
        <button
          id="modify-plan-btn"
          onClick={onModify}
          disabled={loading}
          className="flex flex-col items-center gap-2 px-4 py-4 rounded-xl border-2 border-brand-200 text-brand-600 font-semibold hover:bg-brand-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
          aria-label="Request specific modifications to the plan"
        >
          <Edit3 className="w-6 h-6" aria-hidden="true" />
          <span className="text-sm">Modify Plan</span>
        </button>
      </div>

      <p className="text-center text-xs text-slate-400 mt-4">
        All actions interact with the live AI planning workflow.
      </p>
    </div>
  );
}
