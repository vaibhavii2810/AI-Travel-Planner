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
    <div className="space-y-6 animate-fade-in">
      {/* Day cards */}
      {sortedDays.map((day) => (
        <DayCard key={day.day_number} day={day} currency={currency} />
      ))}

      {/* Overall tips */}
      {itinerary.overall_tips && itinerary.overall_tips.length > 0 && (
        <div className="bg-amber-50 rounded-2xl border border-amber-100 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Lightbulb className="w-5 h-5 text-amber-500" aria-hidden="true" />
            <h3 className="text-sm font-bold text-amber-800 uppercase tracking-wide">
              Travel Tips
            </h3>
          </div>
          <ul className="space-y-2">
            {itinerary.overall_tips.map((tip, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-amber-700">
                <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-amber-400 flex-shrink-0" aria-hidden="true" />
                {tip}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Packing suggestions */}
      {itinerary.packing_suggestions && itinerary.packing_suggestions.length > 0 && (
        <div className="bg-slate-50 rounded-2xl border border-slate-100 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Package className="w-5 h-5 text-slate-500" aria-hidden="true" />
            <h3 className="text-sm font-bold text-slate-600 uppercase tracking-wide">
              Packing List
            </h3>
          </div>
          <ul className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1.5">
            {itinerary.packing_suggestions.map((item, i) => (
              <li key={i} className="flex items-center gap-2 text-sm text-slate-600">
                <span className="w-1.5 h-1.5 rounded-full bg-slate-400 flex-shrink-0" aria-hidden="true" />
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
