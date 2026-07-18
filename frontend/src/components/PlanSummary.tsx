import { MapPin, Calendar, Users, DollarSign, Tag } from 'lucide-react';
import type { TravelPlan } from '@/types/api';

interface PlanSummaryProps { plan: TravelPlan }

export function PlanSummary({ plan }: PlanSummaryProps) {
  const req = plan.travel_request;
  if (!req) return null;

  const startDate = req.start_date
    ? new Date(req.start_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    : null;
  const endDate = req.end_date
    ? new Date(req.end_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    : null;

  const nights = req.start_date && req.end_date
    ? Math.max(0, Math.floor((new Date(req.end_date).getTime() - new Date(req.start_date).getTime()) / 86_400_000))
    : null;

  const metaItems = [
    req.destination && { icon: MapPin, color: '#22c55e', label: req.destination },
    (startDate && endDate) && { icon: Calendar, color: '#60a5fa', label: `${startDate} → ${endDate}${nights != null ? ` (${nights}n)` : ''}` },
    req.num_travelers && { icon: Users, color: '#a78bfa', label: `${req.num_travelers} traveller${req.num_travelers > 1 ? 's' : ''}` },
    (req.budget_min != null || req.budget_max != null) && {
      icon: DollarSign, color: '#f59e0b',
      label: `${req.budget_currency ?? 'USD'} ${req.budget_min?.toLocaleString() ?? '?'} – ${req.budget_max?.toLocaleString() ?? '?'}`,
    },
  ].filter(Boolean) as { icon: React.ElementType; color: string; label: string }[];

  return (
    <div style={{
      background: 'var(--bg-card)', border: '1px solid var(--border)',
      borderRadius: '16px', padding: '18px 20px',
      boxShadow: 'var(--shadow-card)',
    }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '16px', flexWrap: 'wrap' }}>
        {/* Left: Title + meta */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <h2 style={{
            fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '18px',
            color: 'var(--text-primary)', marginBottom: '10px', lineHeight: 1.2,
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            {req.destination ?? 'Trip Plan'}
          </h2>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '14px' }}>
            {metaItems.map(({ icon: Icon, color, label }, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <Icon size={13} color={color} />
                <span style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1 }}>{label}</span>
              </div>
            ))}
          </div>

          {/* Interests */}
          {req.interests && req.interests.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '10px', flexWrap: 'wrap' }}>
              <Tag size={11} color="var(--text-muted)" />
              {req.interests.map(interest => (
                <span key={interest} style={{
                  padding: '2px 9px', borderRadius: '99px',
                  background: 'var(--accent-glow)', border: '1px solid var(--accent-border)',
                  fontSize: '11px', fontWeight: 600, color: 'var(--accent)',
                  textTransform: 'capitalize',
                }}>
                  {interest}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Status badge */}
        <StatusPill status={plan.status} />
      </div>
    </div>
  );
}

const STATUS_CONFIG: Record<string, { label: string; bg: string; color: string; dot: string }> = {
  queued:                  { label: 'Queued',          bg: 'rgba(148,163,184,0.1)', color: '#94a3b8', dot: '#94a3b8' },
  researching:             { label: 'Researching',     bg: 'rgba(96,165,250,0.1)',  color: '#60a5fa', dot: '#60a5fa' },
  planning:                { label: 'Planning',        bg: 'rgba(167,139,250,0.1)', color: '#a78bfa', dot: '#a78bfa' },
  revising:                { label: 'Revising',        bg: 'rgba(251,191,36,0.1)',  color: '#fbbf24', dot: '#fbbf24' },
  awaiting_review:         { label: 'Awaiting Review', bg: 'rgba(251,191,36,0.1)',  color: '#fbbf24', dot: '#fbbf24' },
  finalized:               { label: 'Finalised ✓',    bg: 'rgba(34,197,94,0.1)',   color: '#22c55e', dot: '#22c55e' },
  error:                   { label: 'Error',           bg: 'rgba(248,113,113,0.1)', color: '#f87171', dot: '#f87171' },
  max_revisions_exceeded:  { label: 'Max Revisions',   bg: 'rgba(248,113,113,0.1)', color: '#f87171', dot: '#f87171' },
};

function StatusPill({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] ?? { label: status, bg: 'var(--bg-surface)', color: 'var(--text-muted)', dot: 'var(--text-muted)' };
  const isActive = ['researching', 'planning', 'revising', 'queued'].includes(status);
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '7px',
      padding: '5px 12px', borderRadius: '99px',
      background: cfg.bg,
      border: `1px solid ${cfg.color}33`,
      flexShrink: 0,
    }}>
      <div style={{
        width: '7px', height: '7px', borderRadius: '50%', background: cfg.dot, flexShrink: 0,
        animation: isActive ? 'blink 1.4s ease-in-out infinite' : undefined,
      }} />
      <span style={{ fontSize: '12px', fontWeight: 700, color: cfg.color, whiteSpace: 'nowrap' }}>
        {cfg.label}
      </span>
    </div>
  );
}
