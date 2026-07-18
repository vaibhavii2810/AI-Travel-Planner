import { CheckCircle, XCircle, Edit3 } from 'lucide-react';

interface ReviewActionsProps {
  loading: boolean;
  onApprove: () => void;
  onReject: () => void;
  onModify: () => void;
  revisionCount: number;
}

export function ReviewActions({ loading, onApprove, onReject, onModify, revisionCount }: ReviewActionsProps) {
  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--accent-border)',
      borderRadius: '16px',
      overflow: 'hidden',
      boxShadow: '0 0 24px var(--accent-glow)',
    }}>
      {/* Header */}
      <div style={{
        padding: '16px 24px',
        borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div>
          <h3 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '16px', color: 'var(--text-primary)', marginBottom: '3px' }}>
            Review Your Plan
          </h3>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            Scroll through the itinerary below, then approve, request changes, or reject.
          </p>
        </div>
        {revisionCount > 0 && (
          <span style={{
            padding: '4px 12px', borderRadius: '99px', fontSize: '11px', fontWeight: 600,
            background: 'rgba(251,191,36,0.1)', border: '1px solid rgba(251,191,36,0.25)',
            color: '#fbbf24',
          }}>
            Revision {revisionCount}
          </span>
        )}
      </div>

      {/* Actions */}
      <div style={{ padding: '16px 24px', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
        {/* Approve */}
        <button
          onClick={onApprove}
          disabled={loading}
          style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            padding: '11px 22px',
            borderRadius: '10px',
            background: 'var(--accent)',
            border: '1px solid var(--accent)',
            color: '#000',
            fontSize: '14px', fontWeight: 700,
            cursor: loading ? 'not-allowed' : 'pointer',
            opacity: loading ? 0.6 : 1,
            transition: 'all 0.15s',
            boxShadow: '0 0 16px var(--accent-glow)',
          }}
          onMouseEnter={e => { if (!loading) (e.currentTarget as HTMLElement).style.boxShadow = '0 0 28px rgba(34,197,94,0.4)'; }}
          onMouseLeave={e => { (e.currentTarget as HTMLElement).style.boxShadow = '0 0 16px var(--accent-glow)'; }}
        >
          <CheckCircle size={16} /> Approve Plan
        </button>

        {/* Modify */}
        <button
          onClick={onModify}
          disabled={loading}
          style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            padding: '11px 22px',
            borderRadius: '10px',
            background: 'transparent',
            border: '1px solid var(--border)',
            color: 'var(--text-primary)',
            fontSize: '14px', fontWeight: 600,
            cursor: loading ? 'not-allowed' : 'pointer',
            opacity: loading ? 0.6 : 1,
            transition: 'all 0.15s',
          }}
          onMouseEnter={e => { if (!loading) {
            (e.currentTarget as HTMLElement).style.borderColor = 'var(--border-hover)';
            (e.currentTarget as HTMLElement).style.background = 'var(--bg-card-hover)';
          }}}
          onMouseLeave={e => {
            (e.currentTarget as HTMLElement).style.borderColor = 'var(--border)';
            (e.currentTarget as HTMLElement).style.background = 'transparent';
          }}
        >
          <Edit3 size={16} /> Modify
        </button>

        {/* Reject */}
        <button
          onClick={onReject}
          disabled={loading}
          style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            padding: '11px 22px',
            borderRadius: '10px',
            background: 'transparent',
            border: '1px solid rgba(248,113,113,0.3)',
            color: '#f87171',
            fontSize: '14px', fontWeight: 600,
            cursor: loading ? 'not-allowed' : 'pointer',
            opacity: loading ? 0.6 : 1,
            transition: 'all 0.15s',
          }}
          onMouseEnter={e => { if (!loading) {
            (e.currentTarget as HTMLElement).style.borderColor = 'rgba(248,113,113,0.55)';
            (e.currentTarget as HTMLElement).style.background = 'rgba(248,113,113,0.06)';
          }}}
          onMouseLeave={e => {
            (e.currentTarget as HTMLElement).style.borderColor = 'rgba(248,113,113,0.3)';
            (e.currentTarget as HTMLElement).style.background = 'transparent';
          }}
        >
          <XCircle size={16} /> Reject
        </button>
      </div>
    </div>
  );
}
