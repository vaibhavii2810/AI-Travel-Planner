import { Calendar, Users, Wallet, Hash, MapPin } from 'lucide-react';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { formatDate, formatCurrency, formatDateRange } from '@/utils/format';
import type { PlanStatusResponse } from '@/types/api';

interface PlanSummaryProps {
  plan: PlanStatusResponse;
}

export function PlanSummary({ plan }: PlanSummaryProps) {
  const req = plan.travel_request;

  return (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-card p-6 animate-fade-in">
      {/* Header row */}
      <div className="flex flex-wrap items-start justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <MapPin className="w-5 h-5 text-brand-500" aria-hidden="true" />
            <h2 className="text-xl font-bold text-slate-900">
              {req?.destination ?? 'Your Trip'}
            </h2>
          </div>
          {req && (
            <p className="text-sm text-slate-500 pl-7">
              {formatDateRange(req.start_date, req.end_date)}
            </p>
          )}
        </div>
        <StatusBadge status={plan.status} />
      </div>

      {/* Metadata grid */}
      <dl className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {req && (
          <>
            <div className="flex flex-col gap-1">
              <dt className="flex items-center gap-1.5 text-xs font-medium text-slate-400 uppercase tracking-wide">
                <Calendar className="w-3.5 h-3.5" aria-hidden="true" />
                Dates
              </dt>
              <dd className="text-sm font-semibold text-slate-800">
                {formatDate(req.start_date)} –<br />
                {formatDate(req.end_date)}
              </dd>
            </div>

            <div className="flex flex-col gap-1">
              <dt className="flex items-center gap-1.5 text-xs font-medium text-slate-400 uppercase tracking-wide">
                <Users className="w-3.5 h-3.5" aria-hidden="true" />
                Travelers
              </dt>
              <dd className="text-sm font-semibold text-slate-800">
                {req.num_travelers} {req.num_travelers === 1 ? 'person' : 'people'}
              </dd>
            </div>

            <div className="flex flex-col gap-1">
              <dt className="flex items-center gap-1.5 text-xs font-medium text-slate-400 uppercase tracking-wide">
                <Wallet className="w-3.5 h-3.5" aria-hidden="true" />
                Budget
              </dt>
              <dd className="text-sm font-semibold text-slate-800">
                {formatCurrency(req.budget_min, req.budget_currency)} – {formatCurrency(req.budget_max, req.budget_currency)}
              </dd>
            </div>
          </>
        )}

        <div className="flex flex-col gap-1">
          <dt className="flex items-center gap-1.5 text-xs font-medium text-slate-400 uppercase tracking-wide">
            <Hash className="w-3.5 h-3.5" aria-hidden="true" />
            Plan ID
          </dt>
          <dd className="text-sm font-mono text-slate-600 break-all">
            {plan.plan_id.slice(0, 18)}…
          </dd>
        </div>
      </dl>

      {/* Interests chips */}
      {req?.interests && req.interests.length > 0 && (
        <div className="mt-5 pt-5 border-t border-slate-50">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-2">Interests</p>
          <div className="flex flex-wrap gap-1.5">
            {req.interests.map((interest) => (
              <span
                key={interest}
                className="px-2.5 py-0.5 bg-brand-50 text-brand-700 text-xs font-medium rounded-full border border-brand-100"
              >
                {interest}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Revision indicator */}
      {plan.revision_count > 0 && (
        <p className="mt-3 text-xs text-slate-400">
          Revision {plan.revision_count}
        </p>
      )}
    </div>
  );
}
