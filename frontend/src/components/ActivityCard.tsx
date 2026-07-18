import { Clock, MapPin, DollarSign, AlertCircle } from 'lucide-react';
import { formatCurrency, formatDuration } from '@/utils/format';
import type { Activity } from '@/types/api';

interface ActivityCardProps {
  activity: Activity;
  currency?: string;
}

export function ActivityCard({ activity, currency = 'USD' }: ActivityCardProps) {
  return (
    <div className="bg-slate-50 rounded-xl p-4 border border-slate-100 hover:border-brand-200 hover:shadow-sm transition-all duration-150">
      <h5 className="text-sm font-semibold text-slate-800 leading-snug mb-1">
        {activity.name}
      </h5>

      {activity.description && (
        <p className="text-xs text-slate-500 leading-relaxed mb-3">{activity.description}</p>
      )}

      {/* Meta row */}
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {activity.location && (
          <span className="flex items-center gap-1 text-xs text-slate-400">
            <MapPin className="w-3 h-3" aria-hidden="true" />
            {activity.location}
          </span>
        )}
        {activity.duration_minutes > 0 && (
          <span className="flex items-center gap-1 text-xs text-slate-400">
            <Clock className="w-3 h-3" aria-hidden="true" />
            {formatDuration(activity.duration_minutes)}
          </span>
        )}
        {activity.estimated_cost_per_person > 0 && (
          <span className="flex items-center gap-1 text-xs text-emerald-600 font-medium">
            <DollarSign className="w-3 h-3" aria-hidden="true" />
            {formatCurrency(activity.estimated_cost_per_person, currency)}/person
          </span>
        )}
        {activity.estimated_cost_per_person === 0 && (
          <span className="text-xs text-emerald-600 font-medium">Free</span>
        )}
      </div>

      {/* Booking required badge */}
      {activity.booking_required && (
        <div className="mt-2 flex items-center gap-1 text-[11px] text-amber-600 font-medium">
          <AlertCircle className="w-3 h-3" aria-hidden="true" />
          Booking required
        </div>
      )}

      {/* Tips */}
      {activity.tips && (
        <p className="mt-2 text-[11px] text-slate-400 italic">{activity.tips}</p>
      )}
    </div>
  );
}
