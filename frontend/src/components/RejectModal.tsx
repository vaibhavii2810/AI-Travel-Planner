import { useState } from 'react';
import { X, XCircle, Send } from 'lucide-react';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

interface RejectModalProps {
  open: boolean;
  loading: boolean;
  onSubmit: (feedback: string) => void;
  onClose: () => void;
}

const PLACEHOLDER_EXAMPLES = [
  'Add more outdoor activities for an active trip.',
  'Reduce expensive activities to fit a tighter budget.',
  'I prefer more cultural and historical experiences.',
  'Add some free time / downtime in the schedule.',
];

export function RejectModal({ open, loading, onSubmit, onClose }: RejectModalProps) {
  const [feedback, setFeedback] = useState('');
  const [error, setError] = useState('');

  if (!open) return null;

  const handleSubmit = () => {
    if (!feedback.trim()) {
      setError('Please describe what you would like the AI to improve.');
      return;
    }
    setError('');
    onSubmit(feedback.trim());
  };

  const handleClose = () => {
    if (!loading) {
      setFeedback('');
      setError('');
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-fade-in"
      role="dialog"
      aria-modal="true"
      aria-labelledby="reject-modal-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) handleClose();
      }}
    >
      <div className="bg-white rounded-2xl shadow-modal w-full max-w-lg p-6 animate-slide-up">
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-red-50 flex items-center justify-center">
              <XCircle className="w-5 h-5 text-red-500" aria-hidden="true" />
            </div>
            <div>
              <h2 id="reject-modal-title" className="text-lg font-bold text-slate-900">
                Request Revisions
              </h2>
              <p className="text-xs text-slate-500">Tell the AI what to improve</p>
            </div>
          </div>
          <button
            onClick={handleClose}
            disabled={loading}
            className="text-slate-400 hover:text-slate-600 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 rounded-lg p-1"
            aria-label="Close"
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        <p className="text-sm text-slate-600 mb-4 leading-relaxed">
          Describe what you'd like changed. The AI agents will use your feedback to 
          research and build a revised itinerary.
        </p>

        {/* Suggestion pills */}
        <div className="mb-3">
          <p className="text-xs text-slate-400 mb-2 font-medium">Quick suggestions (click to use):</p>
          <div className="flex flex-wrap gap-2">
            {PLACEHOLDER_EXAMPLES.map((ex) => (
              <button
                key={ex}
                type="button"
                onClick={() => {
                  setFeedback(ex);
                  setError('');
                }}
                className="text-xs px-3 py-1.5 rounded-full border border-slate-200 text-slate-600 hover:border-brand-300 hover:text-brand-700 hover:bg-brand-50 transition-colors"
              >
                {ex.slice(0, 40)}…
              </button>
            ))}
          </div>
        </div>

        {/* Textarea */}
        <div>
          <label htmlFor="reject-feedback" className="block text-sm font-medium text-slate-700 mb-1.5">
            Your feedback <span className="text-red-500" aria-hidden="true">*</span>
          </label>
          <textarea
            id="reject-feedback"
            value={feedback}
            onChange={(e) => {
              setFeedback(e.target.value);
              if (e.target.value.trim()) setError('');
            }}
            disabled={loading}
            rows={4}
            maxLength={2000}
            placeholder="E.g. Add more outdoor activities and reduce the number of museum visits…"
            className={`w-full px-4 py-3 rounded-xl border text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none disabled:opacity-50 transition-colors ${
              error ? 'border-red-300 bg-red-50' : 'border-slate-200 bg-slate-50'
            }`}
          />
          <div className="flex items-center justify-between mt-1">
            {error ? (
              <p className="text-xs text-red-500">{error}</p>
            ) : (
              <span />
            )}
            <p className="text-xs text-slate-400 text-right">{feedback.length}/2000</p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-3 mt-5">
          <button
            onClick={handleClose}
            disabled={loading}
            className="flex-1 px-4 py-2.5 rounded-xl border border-slate-200 text-slate-600 text-sm font-medium hover:bg-slate-50 disabled:opacity-50 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400"
          >
            Cancel
          </button>
          <button
            id="submit-reject-btn"
            onClick={handleSubmit}
            disabled={loading || !feedback.trim()}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-brand-600 text-white text-sm font-semibold hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
          >
            {loading ? (
              <>
                <LoadingSpinner size="sm" className="text-white" />
                Submitting…
              </>
            ) : (
              <>
                <Send className="w-4 h-4" aria-hidden="true" />
                Send Feedback
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
