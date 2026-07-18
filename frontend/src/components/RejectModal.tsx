import { useState } from 'react';
import { X, XCircle, Send } from 'lucide-react';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

interface RejectModalProps {
  open: boolean;
  loading: boolean;
  onSubmit: (feedback: string) => void;
  onClose: () => void;
}

const EXAMPLES = [
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
    <div className="modal-backdrop" onClick={e => { if (e.target === e.currentTarget) handleClose(); }}>
      <div className="modal-panel" style={{ padding: '24px' }}>
        
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '44px', height: '44px', borderRadius: '50%',
              background: 'rgba(248,113,113,0.1)',
              border: '1px solid rgba(248,113,113,0.25)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <XCircle size={18} color="#f87171" />
            </div>
            <div>
              <h2 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '18px', color: 'var(--text-primary)' }}>
                Request Revisions
              </h2>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Tell the AI what to improve</p>
            </div>
          </div>
          <button
            onClick={handleClose}
            disabled={loading}
            style={{
              background: 'transparent', border: 'none', cursor: 'pointer',
              color: 'var(--text-muted)', padding: '4px',
            }}
          >
            <X size={18} />
          </button>
        </div>

        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '16px', lineHeight: 1.6 }}>
          Describe what you'd like changed. The AI agents will use your feedback to 
          research and build a revised itinerary.
        </p>

        {/* Suggestion pills */}
        <div style={{ marginBottom: '16px' }}>
          <p style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>
            Quick suggestions (click to use)
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {EXAMPLES.map(ex => (
              <button
                key={ex}
                type="button"
                onClick={() => { setFeedback(ex); setError(''); }}
                style={{
                  fontSize: '11px', padding: '6px 12px', borderRadius: '99px',
                  background: 'var(--bg-surface)', border: '1px solid var(--border)',
                  color: 'var(--text-secondary)', cursor: 'pointer',
                  transition: 'all 0.15s',
                }}
                onMouseEnter={e => {
                  (e.currentTarget as HTMLElement).style.borderColor = 'rgba(248,113,113,0.5)';
                  (e.currentTarget as HTMLElement).style.color = '#f87171';
                }}
                onMouseLeave={e => {
                  (e.currentTarget as HTMLElement).style.borderColor = 'var(--border)';
                  (e.currentTarget as HTMLElement).style.color = 'var(--text-secondary)';
                }}
              >
                {ex.slice(0, 40)}…
              </button>
            ))}
          </div>
        </div>

        {/* Textarea */}
        <div style={{ marginBottom: '20px' }}>
          <label htmlFor="reject-feedback" style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '8px' }}>
            Your feedback <span style={{ color: '#f87171' }}>*</span>
          </label>
          <textarea
            id="reject-feedback"
            value={feedback}
            onChange={e => {
              setFeedback(e.target.value);
              if (e.target.value.trim()) setError('');
            }}
            disabled={loading}
            rows={4}
            maxLength={2000}
            placeholder="E.g. Add more outdoor activities and reduce the number of museum visits…"
            style={{
              width: '100%', padding: '12px', borderRadius: '10px',
              fontFamily: 'inherit', fontSize: '14px', color: 'var(--text-primary)',
              background: error ? 'rgba(248,113,113,0.05)' : 'var(--bg-input)',
              border: `1px solid ${error ? 'rgba(248,113,113,0.5)' : 'var(--border)'}`,
              resize: 'none', outline: 'none',
              transition: 'border-color 0.15s, box-shadow 0.15s',
            }}
            onFocus={e => {
              e.target.style.borderColor = '#f87171';
              e.target.style.boxShadow = '0 0 0 3px rgba(248,113,113,0.15)';
            }}
            onBlur={e => {
              e.target.style.borderColor = error ? 'rgba(248,113,113,0.5)' : 'var(--border)';
              e.target.style.boxShadow = '';
            }}
          />
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '6px' }}>
            {error ? <p style={{ fontSize: '11px', color: '#f87171' }}>{error}</p> : <span />}
            <p style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{feedback.length}/2000</p>
          </div>
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            onClick={handleClose}
            disabled={loading}
            style={{
              flex: 1, padding: '11px', borderRadius: '10px',
              background: 'transparent', border: '1px solid var(--border)',
              color: 'var(--text-secondary)', fontSize: '14px', fontWeight: 600,
              cursor: 'pointer', transition: 'all 0.15s',
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading || !feedback.trim()}
            style={{
              flex: 1, padding: '11px', borderRadius: '10px',
              background: 'rgba(248,113,113,0.1)', border: '1px solid rgba(248,113,113,0.3)',
              color: '#f87171', fontSize: '14px', fontWeight: 700,
              cursor: loading || !feedback.trim() ? 'not-allowed' : 'pointer',
              opacity: loading || !feedback.trim() ? 0.7 : 1,
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
              transition: 'all 0.15s',
            }}
            onMouseEnter={e => {
              if (!loading && feedback.trim()) {
                (e.currentTarget as HTMLElement).style.background = 'rgba(248,113,113,0.15)';
                (e.currentTarget as HTMLElement).style.borderColor = 'rgba(248,113,113,0.5)';
              }
            }}
            onMouseLeave={e => {
              (e.currentTarget as HTMLElement).style.background = 'rgba(248,113,113,0.1)';
              (e.currentTarget as HTMLElement).style.borderColor = 'rgba(248,113,113,0.3)';
            }}
          >
            {loading ? (
              <>
                <LoadingSpinner size="sm" />
                Submitting…
              </>
            ) : (
              <>
                <Send size={16} />
                Send Feedback
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
