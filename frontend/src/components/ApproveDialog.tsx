import { CheckCircle, X } from 'lucide-react';

interface ApproveDialogProps {
  open: boolean;
  loading: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ApproveDialog({ open, loading, onConfirm, onCancel }: ApproveDialogProps) {
  if (!open) return null;
  return (
    <div className="modal-backdrop" onClick={e => { if (e.target === e.currentTarget) onCancel(); }}>
      <div className="modal-panel">
        <div style={{ padding: '28px' }}>
          {/* Icon */}
          <div style={{
            width: '52px', height: '52px', borderRadius: '50%',
            background: 'rgba(34,197,94,0.12)',
            border: '2px solid var(--accent-border)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            marginBottom: '18px',
          }}>
            <CheckCircle size={22} color="var(--accent)" />
          </div>

          <h2 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '20px', color: 'var(--text-primary)', marginBottom: '8px' }}>
            Approve this itinerary?
          </h2>
          <p style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.65, marginBottom: '24px' }}>
            Approving will finalise your travel plan. The AI workflow will lock in this itinerary and generate your final trip document.
            This action <strong style={{ color: 'var(--text-primary)' }}>cannot be undone</strong> — but you can always create a new plan.
          </p>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              onClick={onCancel}
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
              onClick={onConfirm}
              disabled={loading}
              style={{
                flex: 1, padding: '11px', borderRadius: '10px',
                background: 'var(--accent)', border: '1px solid var(--accent)',
                color: '#000', fontSize: '14px', fontWeight: 700,
                cursor: loading ? 'not-allowed' : 'pointer',
                opacity: loading ? 0.7 : 1,
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                transition: 'all 0.15s',
                boxShadow: '0 0 20px var(--accent-glow)',
              }}
            >
              <CheckCircle size={16} />
              {loading ? 'Approving…' : 'Yes, Approve'}
            </button>
          </div>
        </div>

        {/* Close */}
        <button
          onClick={onCancel}
          style={{
            position: 'absolute', top: '16px', right: '16px',
            background: 'transparent', border: 'none', cursor: 'pointer',
            color: 'var(--text-muted)', padding: '4px',
          }}
        >
          <X size={18} />
        </button>
      </div>
    </div>
  );
}
