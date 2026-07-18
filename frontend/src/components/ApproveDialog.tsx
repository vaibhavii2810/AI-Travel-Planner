import { X, CheckCircle } from 'lucide-react';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

interface ApproveDialogProps {
  open: boolean;
  loading: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ApproveDialog({ open, loading, onConfirm, onCancel }: ApproveDialogProps) {
  if (!open) return null;

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-fade-in"
      role="dialog"
      aria-modal="true"
      aria-labelledby="approve-dialog-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
    >
      <div className="bg-white rounded-2xl shadow-modal w-full max-w-md p-6 animate-slide-up">
        {/* Icon */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-emerald-50 flex items-center justify-center">
              <CheckCircle className="w-5 h-5 text-emerald-600" aria-hidden="true" />
            </div>
            <h2 id="approve-dialog-title" className="text-lg font-bold text-slate-900">
              Approve this itinerary?
            </h2>
          </div>
          <button
            onClick={onCancel}
            disabled={loading}
            className="text-slate-400 hover:text-slate-600 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 rounded-lg p-1"
            aria-label="Cancel"
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        <p className="text-sm text-slate-600 mb-6 leading-relaxed">
          Approving will finalize your travel plan. The AI workflow will lock in this itinerary 
          and generate your final trip document. This action cannot be undone — but you can 
          always create a new plan.
        </p>

        <div className="flex gap-3">
          <button
            onClick={onCancel}
            disabled={loading}
            className="flex-1 px-4 py-2.5 rounded-xl border border-slate-200 text-slate-600 text-sm font-medium hover:bg-slate-50 disabled:opacity-50 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1"
          >
            Cancel
          </button>
          <button
            id="confirm-approve-btn"
            onClick={onConfirm}
            disabled={loading}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-600 text-white text-sm font-semibold hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2"
          >
            {loading ? (
              <>
                <LoadingSpinner size="sm" className="text-white" />
                Approving…
              </>
            ) : (
              <>
                <CheckCircle className="w-4 h-4" aria-hidden="true" />
                Yes, Approve
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
