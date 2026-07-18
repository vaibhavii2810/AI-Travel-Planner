import { useState } from 'react';
import { X, Edit3, Send } from 'lucide-react';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

interface ModifyModalProps {
  open: boolean;
  loading: boolean;
  onSubmit: (instructions: string) => void;
  onClose: () => void;
}

const EXAMPLES = [
  'Replace the Day 2 evening activity with a quieter experience.',
  'Swap the Day 1 morning activity for something more adventurous.',
  'Add a spa or wellness experience on the last day.',
  'Replace one restaurant with a local street food market.',
];

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

  return (
    <div className="modal-backdrop" onClick={e => { if (e.target === e.currentTarget) handleClose(); }}>
      <div className="modal-panel" style={{ padding: '24px' }}>
        
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '44px', height: '44px', borderRadius: '50%',
              background: 'var(--accent-glow)',
              border: '1px solid var(--accent-border)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Edit3 size={18} color="var(--accent)" />
            </div>
            <div>
              <h2 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '18px', color: 'var(--text-primary)' }}>
                Modify Itinerary
              </h2>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Targeted changes to your plan</p>
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
          Describe specific changes you'd like to make. The AI planner will apply 
          your modifications and return an updated itinerary for review.
        </p>

        {/* Suggestion pills */}
        <div style={{ marginBottom: '16px' }}>
          <p style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>
            Examples (click to use)
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {EXAMPLES.map(ex => (
              <button
                key={ex}
                type="button"
                onClick={() => { setInstructions(ex); setError(''); }}
                style={{
                  fontSize: '11px', padding: '6px 12px', borderRadius: '99px',
                  background: 'var(--bg-surface)', border: '1px solid var(--border)',
                  color: 'var(--text-secondary)', cursor: 'pointer',
                  transition: 'all 0.15s',
                }}
                onMouseEnter={e => {
                  (e.currentTarget as HTMLElement).style.borderColor = 'var(--accent-border)';
                  (e.currentTarget as HTMLElement).style.color = 'var(--accent)';
                }}
                onMouseLeave={e => {
                  (e.currentTarget as HTMLElement).style.borderColor = 'var(--border)';
                  (e.currentTarget as HTMLElement).style.color = 'var(--text-secondary)';
                }}
              >
                {ex.slice(0, 45)}…
              </button>
            ))}
          </div>
        </div>

        {/* Textarea */}
        <div style={{ marginBottom: '20px' }}>
          <label htmlFor="modify-instructions" style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '8px' }}>
            Modification instructions <span style={{ color: '#f87171' }}>*</span>
          </label>
          <textarea
            id="modify-instructions"
            value={instructions}
            onChange={e => {
              setInstructions(e.target.value);
              if (e.target.value.trim()) setError('');
            }}
            disabled={loading}
            rows={4}
            placeholder="E.g. Replace the Day 2 evening activity with a relaxing sunset cruise…"
            style={{
              width: '100%', padding: '12px', borderRadius: '10px',
              fontFamily: 'inherit', fontSize: '14px', color: 'var(--text-primary)',
              background: error ? 'rgba(248,113,113,0.05)' : 'var(--bg-input)',
              border: `1px solid ${error ? 'rgba(248,113,113,0.5)' : 'var(--border)'}`,
              resize: 'none', outline: 'none',
              transition: 'border-color 0.15s, box-shadow 0.15s',
            }}
            onFocus={e => {
              e.target.style.borderColor = 'var(--accent)';
              e.target.style.boxShadow = '0 0 0 3px var(--accent-glow)';
            }}
            onBlur={e => {
              e.target.style.borderColor = error ? 'rgba(248,113,113,0.5)' : 'var(--border)';
              e.target.style.boxShadow = '';
            }}
          />
          {error && <p style={{ fontSize: '11px', color: '#f87171', marginTop: '6px' }}>{error}</p>}
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
            disabled={loading || !instructions.trim()}
            style={{
              flex: 1, padding: '11px', borderRadius: '10px',
              background: 'var(--accent)', border: '1px solid var(--accent)',
              color: '#000', fontSize: '14px', fontWeight: 700,
              cursor: loading || !instructions.trim() ? 'not-allowed' : 'pointer',
              opacity: loading || !instructions.trim() ? 0.7 : 1,
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
              transition: 'all 0.15s',
              boxShadow: loading || !instructions.trim() ? 'none' : '0 0 20px var(--accent-glow)',
            }}
          >
            {loading ? (
              <>
                <LoadingSpinner size="sm" />
                Applying…
              </>
            ) : (
              <>
                <Send size={16} />
                Apply Modifications
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
