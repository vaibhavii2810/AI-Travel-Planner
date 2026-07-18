import { useState } from 'react';
import { X, Edit3, Send } from 'lucide-react';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

interface ModifyModalProps {
  open: boolean;
  loading: boolean;
  onSubmit: (instructions: string) => void;
  onClose: () => void;
}

export function ModifyModal({ open, loading, onSubmit, onClose }: ModifyModalProps) {
  const [instructions, setInstructions] = useState('');
  const [error, setError] = useState('');

  if (!open) return null;

  const handleSubmit = () => {
    if (!instructions.trim()) {
      setError('Please describe the modifications you would like.');
      return;
    }
    setError('');
    onSubmit(instructions.trim());
  };

  const handleClose = () => {
    if (!loading) {
      setInstructions('');
      setError('');
      onClose();
    }
  };

  const examples = [
    'Replace the Day 2 evening activity with a quieter experience.',
    'Swap the Day 1 morning activity for something more adventurous.',
    'Add a spa or wellness experience on the last day.',
    'Replace one restaurant with a local street food market.',
  ];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-fade-in"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modify-modal-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) handleClose();
      }}
    >
      <div className="bg-white rounded-2xl shadow-modal w-full max-w-lg p-6 animate-slide-up">
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-brand-50 flex items-center justify-center">
              <Edit3 className="w-5 h-5 text-brand-500" aria-hidden="true" />
            </div>
            <div>
              <h2 id="modify-modal-title" className="text-lg font-bold text-slate-900">
                Modify Itinerary
              </h2>
              <p className="text-xs text-slate-500">Targeted changes to your plan</p>
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
          Describe specific changes you'd like to make. The AI planner will apply 
          your modifications and return an updated itinerary for review.
        </p>

        {/* Example chips */}
        <div className="mb-3">
          <p className="text-xs text-slate-400 mb-2 font-medium">Examples (click to use):</p>
          <div className="flex flex-wrap gap-2">
            {examples.map((ex) => (
              <button
                key={ex}
                type="button"
                onClick={() => {
                  setInstructions(ex);
                  setError('');
                }}
                className="text-xs px-3 py-1.5 rounded-full border border-slate-200 text-slate-600 hover:border-brand-300 hover:text-brand-700 hover:bg-brand-50 transition-colors"
              >
                {ex.slice(0, 45)}…
              </button>
            ))}
          </div>
        </div>

        {/* Textarea */}
        <div>
          <label htmlFor="modify-instructions" className="block text-sm font-medium text-slate-700 mb-1.5">
            Modification instructions <span className="text-red-500" aria-hidden="true">*</span>
          </label>
          <textarea
            id="modify-instructions"
            value={instructions}
            onChange={(e) => {
              setInstructions(e.target.value);
              if (e.target.value.trim()) setError('');
            }}
            disabled={loading}
            rows={4}
            placeholder="E.g. Replace the Day 2 evening activity with a relaxing sunset cruise…"
            className={`w-full px-4 py-3 rounded-xl border text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none disabled:opacity-50 transition-colors ${
              error ? 'border-red-300 bg-red-50' : 'border-slate-200 bg-slate-50'
            }`}
          />
          {error && <p className="text-xs text-red-500 mt-1">{error}</p>}
        </div>

        {/* Info note about the modifications structure */}
        <p className="text-xs text-slate-400 mt-2 italic">
          Your instructions will be sent as{' '}
          <code className="bg-slate-100 px-1 rounded text-slate-500">modifications.instructions</code>
          {' '}to the AI planner.
        </p>

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
            id="submit-modify-btn"
            onClick={handleSubmit}
            disabled={loading || !instructions.trim()}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-brand-600 text-white text-sm font-semibold hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
          >
            {loading ? (
              <>
                <LoadingSpinner size="sm" className="text-white" />
                Applying…
              </>
            ) : (
              <>
                <Send className="w-4 h-4" aria-hidden="true" />
                Apply Modifications
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
