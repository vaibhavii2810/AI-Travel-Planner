import { CheckCircle, Circle, Loader } from 'lucide-react';

const STEPS = [
  { key: 'researching',     label: 'Research' },
  { key: 'planning',        label: 'Planning' },
  { key: 'awaiting_review', label: 'Your Review' },
  { key: 'finalized',       label: 'Finalised' },
];

const STATUS_ORDER: Record<string, number> = {
  queued:                0,
  researching:           1,
  planning:              2,
  revising:              2,
  awaiting_review:       3,
  finalized:             4,
  error:                 -1,
  max_revisions_exceeded:-1,
};

export function WorkflowStepper({ status }: { status: string }) {
  const current = STATUS_ORDER[status] ?? 0;
  const isError = status === 'error' || status === 'max_revisions_exceeded';
  const isActive = (idx: number) => current === idx + 1;
  const isDone   = (idx: number) => current > idx + 1;

  return (
    <div>
      <div style={{
        display: 'flex', alignItems: 'center', gap: '0',
        overflowX: 'auto',
        paddingBottom: '2px',
      }}>
        {STEPS.map((step, i) => {
          const done   = isDone(i);
          const active = isActive(i);
          const upcoming = !done && !active;

          return (
            <div key={step.key} style={{ display: 'flex', alignItems: 'center', flex: i < STEPS.length - 1 ? 1 : undefined }}>
              {/* Step node */}
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px', minWidth: '72px' }}>
                <div style={{
                  width: '32px', height: '32px', borderRadius: '50%',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: done ? 'var(--accent)' : active ? 'var(--accent-glow)' : 'var(--bg-surface)',
                  border: `2px solid ${done ? 'var(--accent)' : active ? 'var(--accent)' : 'var(--border)'}`,
                  boxShadow: active ? '0 0 0 4px var(--accent-glow)' : undefined,
                  transition: 'all 0.3s ease',
                  flexShrink: 0,
                }}>
                  {done ? (
                    <CheckCircle size={14} color="#000" strokeWidth={3} />
                  ) : active ? (
                    <Loader size={14} color="var(--accent)" strokeWidth={2.5} style={{ animation: 'spin 1.2s linear infinite' }} />
                  ) : (
                    <Circle size={14} color="var(--text-muted)" strokeWidth={1.5} />
                  )}
                </div>
                <span style={{
                  fontSize: '11px',
                  fontWeight: active ? 700 : done ? 600 : 400,
                  color: done ? 'var(--accent)' : active ? 'var(--text-primary)' : 'var(--text-muted)',
                  whiteSpace: 'nowrap',
                  textAlign: 'center',
                }}>
                  {step.label}
                </span>
              </div>

              {/* Connector line */}
              {i < STEPS.length - 1 && (
                <div style={{
                  flex: 1,
                  height: '2px',
                  marginBottom: '18px',
                  background: done
                    ? 'linear-gradient(90deg, var(--accent) 0%, var(--accent-dim) 100%)'
                    : 'var(--border)',
                  borderRadius: '1px',
                  transition: 'background 0.4s ease',
                  minWidth: '24px',
                }} />
              )}
            </div>
          );
        })}
      </div>

      {isError && (
        <p style={{
          marginTop: '12px', padding: '8px 14px',
          background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)',
          borderRadius: '8px', fontSize: '12px', color: '#f87171',
        }}>
          ⚠️ Workflow error — {status === 'max_revisions_exceeded' ? 'maximum revisions reached' : 'an unexpected error occurred'}.
        </p>
      )}
    </div>
  );
}
