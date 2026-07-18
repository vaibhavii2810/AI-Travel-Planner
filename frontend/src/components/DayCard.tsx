import type { DailyPlan } from '@/types/api';
import { ActivityCard } from './ActivityCard';
import { Coffee, Sun, Moon, Hotel } from 'lucide-react';

interface DayCardProps {
  day: DailyPlan;
  currency: string;
}

const SLOT_CONFIG = [
  { key: 'morning',   label: 'Morning',   icon: Coffee, color: '#f59e0b' },
  { key: 'afternoon', label: 'Afternoon', icon: Sun,    color: '#f97316' },
  { key: 'evening',   label: 'Evening',   icon: Moon,   color: '#818cf8' },
] as const;

export function DayCard({ day, currency }: DayCardProps) {
  const date = day.date
    ? new Date(day.date).toLocaleDateString('en-US', {
        weekday: 'short', year: 'numeric', month: 'long', day: 'numeric',
      })
    : null;

  return (
    <div
      style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: '16px',
        overflow: 'hidden',
        boxShadow: 'var(--shadow-card)',
        transition: 'border-color 0.2s, box-shadow 0.2s',
      }}
      onMouseEnter={e => {
        (e.currentTarget as HTMLElement).style.borderColor = 'var(--border-hover)';
        (e.currentTarget as HTMLElement).style.boxShadow = 'var(--shadow-glow)';
      }}
      onMouseLeave={e => {
        (e.currentTarget as HTMLElement).style.borderColor = 'var(--border)';
        (e.currentTarget as HTMLElement).style.boxShadow = 'var(--shadow-card)';
      }}
    >
      {/* Day header */}
      <div style={{
        padding: '16px 20px',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '36px', height: '36px', borderRadius: '10px',
            background: 'var(--accent-glow)',
            border: '1px solid var(--accent-border)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0,
          }}>
            <span style={{ fontSize: '13px', fontWeight: 800, color: 'var(--accent)' }}>
              {day.day_number}
            </span>
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{
                fontFamily: "'Space Grotesk', sans-serif",
                fontWeight: 700, fontSize: '15px',
                color: 'var(--accent)',
              }}>
                Day {day.day_number}
              </span>
              {day.theme && (
                <span style={{
                  padding: '2px 10px', borderRadius: '99px',
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border)',
                  fontSize: '11px', fontWeight: 600,
                  color: 'var(--text-secondary)',
                }}>
                  {day.theme}
                </span>
              )}
            </div>
            {date && (
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                {date}
              </div>
            )}
          </div>
        </div>

        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '2px' }}>Est. daily cost</div>
          <div style={{ fontWeight: 700, fontSize: '16px', color: 'var(--accent)' }}>
            {currency} {day.estimated_daily_cost_per_person?.toFixed(0) ?? '—'}
            <span style={{ fontSize: '11px', fontWeight: 400, color: 'var(--text-muted)' }}>/person</span>
          </div>
        </div>
      </div>

      {/* Slots */}
      <div style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {SLOT_CONFIG.map(({ key, label, icon: Icon, color }) => {
          const activities = (day as Record<string, unknown>)[key] as typeof day.morning;
          if (!activities?.length) return null;
          return (
            <div key={key}>
              <div style={{
                display: 'flex', alignItems: 'center', gap: '7px',
                marginBottom: '10px',
              }}>
                <Icon size={13} color={color} strokeWidth={2} />
                <span style={{
                  fontSize: '11px', fontWeight: 700,
                  letterSpacing: '0.08em', textTransform: 'uppercase',
                  color,
                }}>
                  {label}
                </span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {activities.map((act, i) => (
                  <ActivityCard key={i} activity={act} currency={currency} slotColor={color} />
                ))}
              </div>
            </div>
          );
        })}

        {/* Accommodation */}
        {day.accommodation && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: '10px',
            padding: '10px 14px',
            background: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: '10px',
          }}>
            <Hotel size={14} color="var(--text-muted)" />
            <div>
              <span style={{ fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)' }}>
                Accommodation
              </span>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '1px' }}>
                {day.accommodation}
              </p>
            </div>
          </div>
        )}

        {/* Travel notes */}
        {(day.practical_notes || (day as Record<string, unknown>).travel_notes) && (
          <p style={{
            fontSize: '12px',
            color: 'var(--text-muted)',
            fontStyle: 'italic',
            lineHeight: 1.5,
            borderTop: '1px solid var(--border)',
            paddingTop: '12px',
            marginTop: '4px',
          }}>
            💡 {day.practical_notes || (day as Record<string, unknown>).travel_notes as string}
          </p>
        )}
      </div>
    </div>
  );
}
