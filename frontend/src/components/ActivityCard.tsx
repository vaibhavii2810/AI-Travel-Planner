import type { Activity } from '@/types/api';
import { MapPin, Clock, DollarSign, AlertCircle, Info } from 'lucide-react';

interface ActivityCardProps {
  activity: Activity;
  currency: string;
  slotColor?: string;
}

export function ActivityCard({ activity, currency, slotColor = 'var(--accent)' }: ActivityCardProps) {
  const durationHours = Math.floor((activity.duration_minutes ?? 0) / 60);
  const durationMins  = (activity.duration_minutes ?? 0) % 60;
  const durationStr   = durationHours > 0
    ? `${durationHours}h${durationMins > 0 ? ` ${durationMins}m` : ''}`
    : `${durationMins}m`;

  const hasCost = (activity.estimated_cost_per_person ?? 0) > 0;
  const hasHourlyRate = (activity.cost_per_hour ?? 0) > 0;

  return (
    <div style={{
      background: 'var(--bg-surface)',
      border: `1px solid var(--border)`,
      borderLeft: `3px solid ${slotColor}`,
      borderRadius: '10px',
      padding: '14px 16px',
      transition: 'background 0.2s, border-color 0.2s',
    }}
    onMouseEnter={e => {
      (e.currentTarget as HTMLElement).style.background = 'var(--bg-card-hover)';
      (e.currentTarget as HTMLElement).style.borderColor = 'var(--border-hover)';
    }}
    onMouseLeave={e => {
      (e.currentTarget as HTMLElement).style.background = 'var(--bg-surface)';
      (e.currentTarget as HTMLElement).style.borderColor = 'var(--border)';
    }}
    >
      <p style={{ fontWeight: 600, fontSize: '14px', color: 'var(--text-primary)', marginBottom: '4px', lineHeight: 1.3 }}>
        {activity.name}
      </p>
      {activity.description && (
        <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '10px', lineHeight: 1.55 }}>
          {activity.description}
        </p>
      )}

      {/* Meta row */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'center' }}>
        {activity.location && (
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px', color: 'var(--text-muted)' }}>
            <MapPin size={11} /> {activity.location}
          </span>
        )}
        {activity.duration_minutes != null && activity.duration_minutes > 0 && (
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px', color: 'var(--text-muted)' }}>
            <Clock size={11} /> {durationStr}
          </span>
        )}
        {hasCost && (
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px', fontWeight: 700, color: 'var(--accent)' }}>
            <DollarSign size={11} /> {currency} {activity.estimated_cost_per_person?.toFixed(0)}/person
          </span>
        )}
        {hasHourlyRate && (
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px', color: 'var(--text-muted)' }}>
            ({currency} {activity.cost_per_hour?.toFixed(0)}/hr)
          </span>
        )}
        {activity.booking_required && (
          <span style={{
            display: 'flex', alignItems: 'center', gap: '4px',
            fontSize: '11px', fontWeight: 600,
            color: '#f59e0b',
          }}>
            <AlertCircle size={11} /> Booking required
          </span>
        )}
      </div>

      {/* Tips */}
      {activity.tips && (
        <p style={{
          marginTop: '10px',
          fontSize: '11px',
          color: 'var(--text-muted)',
          fontStyle: 'italic',
          display: 'flex', gap: '5px',
          lineHeight: 1.5,
        }}>
          <Info size={11} style={{ flexShrink: 0, marginTop: '2px', color: 'var(--text-muted)' }} />
          {activity.tips}
        </p>
      )}
    </div>
  );
}
