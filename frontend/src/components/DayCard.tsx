import { Sun, Coffee, Moon, Hotel, DollarSign } from 'lucide-react';
import { ActivityCard } from './ActivityCard';
import { formatDate, formatCurrency } from '@/utils/format';
import type { DailyPlan } from '@/types/api';

interface DayCardProps {
  day: DailyPlan;
  currency?: string;
}

const TIME_SLOTS = [
  { key: 'morning'   as const, label: 'Morning',   Icon: Coffee },
  { key: 'afternoon' as const, label: 'Afternoon',  Icon: Sun    },
  { key: 'evening'   as const, label: 'Evening',    Icon: Moon   },
] as const;

export function DayCard({ day, currency = 'USD' }: DayCardProps) {
  const dateStr = typeof day.date === 'string' ? day.date : String(day.date);

  return (
    <article
      className="bg-white rounded-2xl border border-slate-100 shadow-card overflow-hidden animate-slide-up"
      aria-label={`Day ${day.day_number}`}
    >
      {/* Day header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-50 bg-slate-50/60">
        <div>
          <div className="flex items-baseline gap-3">
            <span className="text-xs font-bold text-brand-600 uppercase tracking-widest">
              Day {day.day_number}
            </span>
            {day.theme && (
              <span className="text-sm text-slate-600 font-medium">{day.theme}</span>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-0.5">{formatDate(dateStr)}</p>
        </div>

        {day.estimated_daily_cost_per_person > 0 && (
          <div className="text-right">
            <p className="text-xs text-slate-400">Est. daily cost</p>
            <p className="text-sm font-bold text-slate-800 flex items-center gap-1 justify-end">
              <DollarSign className="w-3.5 h-3.5 text-emerald-500" aria-hidden="true" />
              {formatCurrency(day.estimated_daily_cost_per_person, currency)}
              <span className="text-xs font-normal text-slate-400">/person</span>
            </p>
          </div>
        )}
      </div>

      <div className="p-6 space-y-6">
        {/* Activity slots */}
        {TIME_SLOTS.map(({ key, label, Icon }) => {
          const activities = day[key];
          if (!activities || activities.length === 0) return null;

          return (
            <div key={key}>
              <div className="flex items-center gap-2 mb-3">
                <Icon className="w-4 h-4 text-slate-400" aria-hidden="true" />
                <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">{label}</h4>
              </div>
              <div className="space-y-2">
                {activities.map((activity, idx) => (
                  <ActivityCard key={idx} activity={activity} currency={currency} />
                ))}
              </div>
            </div>
          );
        })}

        {/* Accommodation */}
        {day.accommodation && (
          <div className="flex items-start gap-2 pt-3 border-t border-slate-50">
            <Hotel className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" aria-hidden="true" />
            <div>
              <p className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-0.5">
                Accommodation
              </p>
              <p className="text-sm text-slate-700">{day.accommodation}</p>
            </div>
          </div>
        )}

        {/* Practical notes (aliased as travel_notes on backend) */}
        {day.practical_notes && (
          <div className="bg-blue-50 rounded-xl px-4 py-3 text-xs text-blue-700 leading-relaxed border border-blue-100">
            <span className="font-semibold">Travel notes: </span>
            {day.practical_notes}
          </div>
        )}
      </div>
    </article>
  );
}
