import { Lightbulb, Package } from 'lucide-react';
import { DayCard } from './DayCard';
import type { DraftItinerary } from '@/types/api';

interface ItineraryTimelineProps {
  itinerary: DraftItinerary;
  currency?: string;
}

export function ItineraryTimeline({ itinerary, currency = 'USD' }: ItineraryTimelineProps) {
  const sortedDays = [...itinerary.daily_plans].sort(
    (a, b) => a.day_number - b.day_number,
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }} className="animate-fade-in">
      {/* Day cards */}
      {sortedDays.map((day) => (
        <DayCard key={day.day_number} day={day} currency={currency} />
      ))}

      {/* Travel Tips */}
      {itinerary.overall_tips && itinerary.overall_tips.length > 0 && (
        <div style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: '16px',
          overflow: 'hidden',
          boxShadow: 'var(--shadow-card)',
        }}>
          {/* Header */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: '10px',
            padding: '14px 20px',
            borderBottom: '1px solid var(--border)',
            background: 'rgba(251,191,36,0.04)',
          }}>
            <div style={{
              width: '32px', height: '32px', borderRadius: '8px',
              background: 'rgba(251,191,36,0.12)',
              border: '1px solid rgba(251,191,36,0.2)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0,
            }}>
              <Lightbulb size={15} color="#fbbf24" />
            </div>
            <h3 style={{
              fontFamily: "'Space Grotesk', sans-serif",
              fontSize: '13px', fontWeight: 700,
              color: 'var(--text-primary)',
              letterSpacing: '0.04em', textTransform: 'uppercase',
            }}>
              Travel Tips
            </h3>
          </div>
          {/* Tips list */}
          <ul style={{
            padding: '16px 20px',
            display: 'flex', flexDirection: 'column', gap: '10px',
            listStyle: 'none',
          }}>
            {itinerary.overall_tips.map((tip, i) => (
              <li key={i} style={{
                display: 'flex', alignItems: 'flex-start', gap: '10px',
                fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.55,
              }}>
                <span style={{
                  marginTop: '6px',
                  width: '6px', height: '6px', borderRadius: '50%',
                  background: '#fbbf24', flexShrink: 0,
                }} />
                {tip}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Packing List */}
      {itinerary.packing_suggestions && itinerary.packing_suggestions.length > 0 && (
        <div style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: '16px',
          overflow: 'hidden',
          boxShadow: 'var(--shadow-card)',
        }}>
          {/* Header */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: '10px',
            padding: '14px 20px',
            borderBottom: '1px solid var(--border)',
            background: 'rgba(96,165,250,0.04)',
          }}>
            <div style={{
              width: '32px', height: '32px', borderRadius: '8px',
              background: 'rgba(96,165,250,0.1)',
              border: '1px solid rgba(96,165,250,0.2)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0,
            }}>
              <Package size={15} color="#60a5fa" />
            </div>
            <h3 style={{
              fontFamily: "'Space Grotesk', sans-serif",
              fontSize: '13px', fontWeight: 700,
              color: 'var(--text-primary)',
              letterSpacing: '0.04em', textTransform: 'uppercase',
            }}>
              Packing List
            </h3>
          </div>
          {/* Grid of items */}
          <div style={{
            padding: '16px 20px',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
            gap: '10px 24px',
          }}>
            {itinerary.packing_suggestions.map((item, i) => (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', gap: '8px',
                fontSize: '13px', color: 'var(--text-secondary)',
              }}>
                <span style={{
                  width: '6px', height: '6px', borderRadius: '50%',
                  background: '#60a5fa', flexShrink: 0,
                }} />
                {item}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
