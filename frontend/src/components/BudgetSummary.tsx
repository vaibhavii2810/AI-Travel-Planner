import { formatCurrency } from '@/utils/format';
import type { BudgetAllocation } from '@/types/api';

interface BudgetSummaryProps {
  budget: BudgetAllocation;
  budgetMax?: number; // from travel_request.budget_max for reference
}

interface BudgetLine {
  label: string;
  value: number;
  color: string;
}

export function BudgetSummary({ budget, budgetMax }: BudgetSummaryProps) {
  const lines: BudgetLine[] = [
    { label: 'Accommodation', value: budget.accommodation_total, color: 'bg-brand-500' },
    { label: 'Food & Dining', value: budget.food_total,          color: 'bg-emerald-500' },
    { label: 'Transportation', value: budget.transport_total,    color: 'bg-violet-500'  },
    { label: 'Activities',     value: budget.activities_total,   color: 'bg-amber-500'   },
    { label: 'Contingency',    value: budget.contingency_total,  color: 'bg-slate-400'   },
  ].filter((l) => l.value > 0);

  const grandTotal = budget.grand_total;
  const reference = budgetMax ?? grandTotal;

  return (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-card p-6 animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-sm font-bold text-slate-700 uppercase tracking-wide">Budget Summary</h3>
        <div className="text-right">
          <p className="text-2xl font-bold text-slate-900">
            {formatCurrency(grandTotal, budget.currency)}
          </p>
          <p className="text-xs text-slate-400">
            {formatCurrency(budget.per_person_total, budget.currency)}/person
          </p>
        </div>
      </div>

      {/* Progress bars */}
      <div className="space-y-3">
        {lines.map(({ label, value, color }) => {
          const pct = reference > 0 ? Math.min((value / reference) * 100, 100) : 0;
          return (
            <div key={label}>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="font-medium text-slate-600">{label}</span>
                <span className="text-slate-500">{formatCurrency(value, budget.currency)}</span>
              </div>
              <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
                <div
                  className={`h-full ${color} rounded-full transition-all duration-500`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Budget vs limit */}
      {budgetMax !== undefined && (
        <div className="mt-5 pt-5 border-t border-slate-50 flex items-center justify-between text-xs">
          <span className="text-slate-400">Budget limit</span>
          <span className="font-semibold text-slate-700">
            {formatCurrency(budgetMax, budget.currency)}
          </span>
        </div>
      )}

      {/* Within budget badge */}
      <div className={`mt-3 text-center text-xs font-semibold px-3 py-1.5 rounded-full ${
        budget.within_budget
          ? 'bg-emerald-50 text-emerald-700'
          : 'bg-rose-50 text-rose-700'
      }`}>
        {budget.within_budget ? '✓ Within budget' : '⚠ Slightly over budget'}
      </div>

      {budget.notes && (
        <p className="mt-3 text-xs text-slate-400 italic text-center">{budget.notes}</p>
      )}
    </div>
  );
}
