import type { PlanStatus } from '@/types/api';

const CONFIG: Record<
  PlanStatus,
  { label: string; className: string }
> = {
  queued:               { label: 'Queued',              className: 'bg-slate-100 text-slate-600' },
  researching:          { label: 'Researching',         className: 'bg-blue-50 text-blue-700 ring-1 ring-blue-200' },
  planning:             { label: 'Building Itinerary',  className: 'bg-violet-50 text-violet-700 ring-1 ring-violet-200' },
  awaiting_review:      { label: 'Awaiting Review',     className: 'bg-amber-50 text-amber-700 ring-1 ring-amber-200' },
  revising:             { label: 'Revising',            className: 'bg-orange-50 text-orange-700 ring-1 ring-orange-200' },
  finalizing:           { label: 'Finalizing',          className: 'bg-teal-50 text-teal-700 ring-1 ring-teal-200' },
  finalized:            { label: 'Approved & Finalized', className: 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200' },
  error:                { label: 'Error',               className: 'bg-red-50 text-red-700 ring-1 ring-red-200' },
  max_revisions_exceeded: { label: 'Max Revisions',    className: 'bg-rose-50 text-rose-700 ring-1 ring-rose-200' },
};

interface StatusBadgeProps {
  status: PlanStatus | string;
  className?: string;
}

export function StatusBadge({ status, className = '' }: StatusBadgeProps) {
  const cfg = CONFIG[status as PlanStatus] ?? {
    label: status,
    className: 'bg-slate-100 text-slate-600',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${cfg.className} ${className}`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current opacity-70 flex-shrink-0" />
      {cfg.label}
    </span>
  );
}
