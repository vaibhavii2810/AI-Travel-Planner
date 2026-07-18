import type { BudgetAllocation } from '@/types/api';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface BudgetSummaryProps {
  budget: BudgetAllocation;
  budgetMax?: number;
}

const ROWS = [
  { key: 'accommodation_total', label: 'Accommodation', color: '#60a5fa' },
  { key: 'food_total',          label: 'Food & Dining',  color: '#34d399' },
  { key: 'activities_total',    label: 'Activities',     color: '#f59e0b' },
  { key: 'transport_total',     label: 'Transport',      color: '#a78bfa' },
  { key: 'contingency_total',   label: 'Contingency',    color: '#94a3b8' },
] as const;

export function BudgetSummary({ budget, budgetMax }: BudgetSummaryProps) {
  const grand   = budget.grand_total ?? 0;
  const perPerson = budget.per_person_total ?? 0;
  const within  = budget.within_budget ?? true;
  const currency = budget.currency ?? 'USD';

  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border)',
      borderRadius: '16px',
      overflow: 'hidden',
      boxShadow: 'var(--shadow-card)',
    }}>
      {/* Grand total header */}
      <div style={{
        padding: '18px 20px',
        borderBottom: '1px solid var(--border)',
        background: within
          ? 'linear-gradient(135deg, rgba(34,197,94,0.08) 0%, transparent 100%)'
          : 'linear-gradient(135deg, rgba(248,113,113,0.08) 0%, transparent 100%)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-muted)' }}>
            Total Budget
          </span>
          <span style={{
            display: 'flex', alignItems: 'center', gap: '4px',
            fontSize: '11px', fontWeight: 600,
            color: within ? 'var(--accent)' : '#f87171',
          }}>
            {within ? <TrendingDown size={12} /> : <TrendingUp size={12} />}
            {within ? 'Within budget' : 'Over budget'}
          </span>
        </div>
        <div>
          <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 800, fontSize: '28px', color: 'var(--text-primary)', lineHeight: 1 }}>
            {currency} {grand.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
            {currency} {perPerson.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })} per person
          </div>
        </div>
        {budgetMax && (
          <div style={{ marginTop: '12px' }}>
            <div style={{
              height: '4px', borderRadius: '2px',
              background: 'var(--border)',
              overflow: 'hidden',
            }}>
              <div style={{
                height: '100%',
                width: `${Math.min((grand / budgetMax) * 100, 100)}%`,
                background: within ? 'var(--accent)' : '#f87171',
                borderRadius: '2px',
                transition: 'width 0.6s ease',
              }} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px' }}>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>0</span>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                Max: {currency} {budgetMax.toLocaleString()}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Breakdown rows */}
      <div style={{ padding: '12px 20px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {ROWS.map(({ key, label, color }) => {
          const val = (budget as Record<string, unknown>)[key] as number ?? 0;
          const pct = grand > 0 ? (val / grand) * 100 : 0;
          return (
            <div key={key}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
                  <div style={{ width: '8px', height: '8px', borderRadius: '2px', background: color, flexShrink: 0 }} />
                  <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{label}</span>
                </div>
                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>
                  {currency} {val.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                </span>
              </div>
              <div style={{ height: '3px', background: 'var(--border)', borderRadius: '2px', overflow: 'hidden' }}>
                <div style={{
                  height: '100%', width: `${pct}%`,
                  background: color, borderRadius: '2px',
                  transition: 'width 0.6s ease',
                }} />
              </div>
            </div>
          );
        })}
      </div>

      {/* Notes */}
      {budget.notes && (
        <div style={{
          padding: '10px 20px',
          borderTop: '1px solid var(--border)',
          fontSize: '11px',
          color: 'var(--text-muted)',
          fontStyle: 'italic',
          lineHeight: 1.5,
        }}>
          {budget.notes}
        </div>
      )}
    </div>
  );
}
