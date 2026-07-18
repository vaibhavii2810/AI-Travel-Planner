import { useState } from 'react';
import { MapPin, Calendar, DollarSign, Users, Plus, X } from 'lucide-react';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import type { CreatePlanRequest } from '@/types/api';

const PRESET_INTERESTS = [
  { label: 'Adventure',  emoji: '🏔️' },
  { label: 'Food',       emoji: '🍜' },
  { label: 'Culture',    emoji: '🎭' },
  { label: 'History',    emoji: '🏛️' },
  { label: 'Nature',     emoji: '🌿' },
  { label: 'Beaches',    emoji: '🏖️' },
  { label: 'Nightlife',  emoji: '🎉' },
  { label: 'Shopping',   emoji: '🛍️' },
  { label: 'Relaxation', emoji: '🧘' },
];

function todayStr()    { return new Date().toISOString().slice(0, 10); }
function tomorrowStr() { const d = new Date(); d.setDate(d.getDate() + 1); return d.toISOString().slice(0, 10); }

interface TravelRequestFormProps {
  onSubmit: (req: CreatePlanRequest) => Promise<void>;
  loading: boolean;
  error?: string | null;
}

const fieldStyle = (hasError: boolean): React.CSSProperties => ({
  width: '100%',
  padding: '10px 14px',
  fontFamily: 'inherit',
  fontSize: '14px',
  color: 'var(--text-primary)',
  background: hasError ? 'rgba(248,113,113,0.05)' : 'var(--bg-input)',
  border: `1px solid ${hasError ? 'rgba(248,113,113,0.5)' : 'var(--border)'}`,
  borderRadius: '10px',
  outline: 'none',
  transition: 'border-color 0.15s, box-shadow 0.15s',
});

const labelStyle: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: '6px',
  fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)',
  letterSpacing: '0.04em', textTransform: 'uppercase',
  marginBottom: '7px',
};

export function TravelRequestForm({ onSubmit, loading, error }: TravelRequestFormProps) {
  const [destination, setDestination] = useState('');
  const [startDate, setStartDate]     = useState('');
  const [endDate, setEndDate]         = useState('');
  const [budgetMin, setBudgetMin]     = useState('');
  const [budgetMax, setBudgetMax]     = useState('');
  const [currency, setCurrency]       = useState('USD');
  const [travelers, setTravelers]     = useState('1');
  const [selectedInterests, setSelectedInterests] = useState<string[]>([]);
  const [customInterest, setCustomInterest]       = useState('');
  const [formErrors, setFormErrors]   = useState<Record<string, string>>({});

  const toggleInterest = (label: string) => {
    setSelectedInterests(prev =>
      prev.includes(label.toLowerCase())
        ? prev.filter(i => i !== label.toLowerCase())
        : [...prev, label.toLowerCase()]
    );
  };

  const addCustomInterest = () => {
    const val = customInterest.trim().toLowerCase();
    if (val && !selectedInterests.includes(val)) setSelectedInterests(prev => [...prev, val]);
    setCustomInterest('');
  };

  const removeInterest = (interest: string) => {
    setSelectedInterests(prev => prev.filter(i => i !== interest));
  };

  const validate = (): boolean => {
    const errors: Record<string, string> = {};
    if (!destination.trim() || destination.trim().length < 2) errors.destination = 'Destination must be at least 2 characters.';
    if (!startDate) errors.startDate = 'Start date is required.';
    if (!endDate)   errors.endDate   = 'End date is required.';
    if (startDate && endDate && endDate <= startDate) errors.endDate = 'End date must be after start date.';
    const min = parseFloat(budgetMin), max = parseFloat(budgetMax);
    if (!budgetMin || isNaN(min) || min <= 0) errors.budgetMin = 'Min budget must be greater than 0.';
    if (!budgetMax || isNaN(max) || max <= 0) errors.budgetMax = 'Max budget must be greater than 0.';
    if (!isNaN(min) && !isNaN(max) && max < min) errors.budgetMax = 'Max budget must be ≥ minimum budget.';
    const t = parseInt(travelers, 10);
    if (isNaN(t) || t < 1 || t > 50) errors.travelers = 'Travelers must be between 1 and 50.';
    if (selectedInterests.length === 0) errors.interests = 'Please select at least one interest.';
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    await onSubmit({
      destination: destination.trim(),
      start_date: startDate,
      end_date: endDate,
      budget_min: parseFloat(budgetMin),
      budget_max: parseFloat(budgetMax),
      budget_currency: currency,
      num_travelers: parseInt(travelers, 10),
      interests: selectedInterests,
    });
  };

  const focusStyle = {
    borderColor: 'var(--accent)',
    boxShadow: '0 0 0 3px var(--accent-glow)',
  };

  const handleFocus = (e: React.FocusEvent<HTMLInputElement | HTMLSelectElement>) => {
    Object.assign(e.target.style, focusStyle);
  };
  const handleBlur = (e: React.FocusEvent<HTMLInputElement | HTMLSelectElement>, hasError: boolean) => {
    e.target.style.borderColor = hasError ? 'rgba(248,113,113,0.5)' : 'var(--border)';
    e.target.style.boxShadow = '';
  };

  return (
    <form onSubmit={handleSubmit} noValidate aria-label="Travel request form" style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>

      {/* API error */}
      {error && (
        <div style={{
          padding: '12px 16px', borderRadius: '10px',
          background: 'rgba(248,113,113,0.07)', border: '1px solid rgba(248,113,113,0.3)',
          fontSize: '13px', color: '#f87171',
        }} role="alert">
          <strong>Error: </strong>{error}
        </div>
      )}

      {/* Destination */}
      <div>
        <label htmlFor="destination" style={labelStyle}>
          <MapPin size={13} color="var(--accent)" /> Destination
        </label>
        <input
          id="destination" type="text"
          value={destination} onChange={e => setDestination(e.target.value)}
          disabled={loading} placeholder="e.g. Kyoto, Japan" maxLength={200} autoComplete="off"
          style={fieldStyle(!!formErrors.destination)}
          onFocus={handleFocus}
          onBlur={e => handleBlur(e, !!formErrors.destination)}
        />
        {formErrors.destination && <p style={{ fontSize: '11px', color: '#f87171', marginTop: '5px' }}>{formErrors.destination}</p>}
      </div>

      {/* Dates */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
        <div>
          <label htmlFor="start-date" style={labelStyle}><Calendar size={13} color="var(--accent)" /> Start Date</label>
          <input
            id="start-date" type="date"
            value={startDate} onChange={e => setStartDate(e.target.value)}
            disabled={loading} min={todayStr()}
            style={{ ...fieldStyle(!!formErrors.startDate), colorScheme: 'dark' }}
            onFocus={handleFocus}
            onBlur={e => handleBlur(e, !!formErrors.startDate)}
          />
          {formErrors.startDate && <p style={{ fontSize: '11px', color: '#f87171', marginTop: '5px' }}>{formErrors.startDate}</p>}
        </div>
        <div>
          <label htmlFor="end-date" style={labelStyle}><Calendar size={13} color="var(--accent)" /> End Date</label>
          <input
            id="end-date" type="date"
            value={endDate} onChange={e => setEndDate(e.target.value)}
            disabled={loading} min={startDate || tomorrowStr()}
            style={{ ...fieldStyle(!!formErrors.endDate), colorScheme: 'dark' }}
            onFocus={handleFocus}
            onBlur={e => handleBlur(e, !!formErrors.endDate)}
          />
          {formErrors.endDate && <p style={{ fontSize: '11px', color: '#f87171', marginTop: '5px' }}>{formErrors.endDate}</p>}
        </div>
      </div>

      {/* Budget */}
      <div>
        <p style={{ ...labelStyle, marginBottom: '10px' }}>
          <DollarSign size={13} color="var(--accent)" /> Budget Range
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
          <div>
            <label htmlFor="currency" style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: '5px' }}>Currency</label>
            <select
              id="currency" value={currency}
              onChange={e => setCurrency(e.target.value)} disabled={loading}
              style={{ ...fieldStyle(false), cursor: 'pointer' }}
              onFocus={handleFocus}
              onBlur={e => handleBlur(e, false)}
            >
              {['USD', 'EUR', 'GBP', 'INR', 'JPY', 'AUD', 'CAD'].map(c => (
                <option key={c} value={c} style={{ background: 'var(--bg-card)' }}>{c}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="budget-min" style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: '5px' }}>Minimum</label>
            <input
              id="budget-min" type="number"
              value={budgetMin} onChange={e => setBudgetMin(e.target.value)}
              disabled={loading} min="1" step="any" placeholder="500"
              style={fieldStyle(!!formErrors.budgetMin)}
              onFocus={handleFocus}
              onBlur={e => handleBlur(e, !!formErrors.budgetMin)}
            />
            {formErrors.budgetMin && <p style={{ fontSize: '11px', color: '#f87171', marginTop: '5px' }}>{formErrors.budgetMin}</p>}
          </div>
          <div>
            <label htmlFor="budget-max" style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: '5px' }}>Maximum</label>
            <input
              id="budget-max" type="number"
              value={budgetMax} onChange={e => setBudgetMax(e.target.value)}
              disabled={loading} min="1" step="any" placeholder="2000"
              style={fieldStyle(!!formErrors.budgetMax)}
              onFocus={handleFocus}
              onBlur={e => handleBlur(e, !!formErrors.budgetMax)}
            />
            {formErrors.budgetMax && <p style={{ fontSize: '11px', color: '#f87171', marginTop: '5px' }}>{formErrors.budgetMax}</p>}
          </div>
        </div>
      </div>

      {/* Travelers */}
      <div>
        <label htmlFor="travelers" style={labelStyle}><Users size={13} color="var(--accent)" /> Number of Travelers</label>
        <input
          id="travelers" type="number"
          value={travelers} onChange={e => setTravelers(e.target.value)}
          disabled={loading} min="1" max="50"
          style={{ ...fieldStyle(!!formErrors.travelers), maxWidth: '120px' }}
          onFocus={handleFocus}
          onBlur={e => handleBlur(e, !!formErrors.travelers)}
        />
        {formErrors.travelers && <p style={{ fontSize: '11px', color: '#f87171', marginTop: '5px' }}>{formErrors.travelers}</p>}
      </div>

      {/* Interests */}
      <div>
        <p style={{ ...labelStyle, marginBottom: '10px' }}>
          Interests & Preferences
          <span style={{ fontSize: '11px', fontWeight: 400, color: 'var(--text-muted)', textTransform: 'none', letterSpacing: 0 }}>
            (select all that apply)
          </span>
        </p>

        {/* Preset chips */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '12px' }}>
          {PRESET_INTERESTS.map(({ label, emoji }) => {
            const val = label.toLowerCase();
            const selected = selectedInterests.includes(val);
            return (
              <button
                key={label} type="button"
                onClick={() => toggleInterest(label)}
                disabled={loading}
                aria-pressed={selected}
                style={{
                  display: 'flex', alignItems: 'center', gap: '6px',
                  padding: '7px 14px',
                  borderRadius: '99px',
                  fontSize: '13px', fontWeight: 600,
                  border: '1px solid',
                  cursor: 'pointer',
                  transition: 'all 0.15s',
                  background: selected ? 'var(--accent)' : 'var(--bg-surface)',
                  borderColor: selected ? 'var(--accent)' : 'var(--border)',
                  color: selected ? '#000' : 'var(--text-secondary)',
                  boxShadow: selected ? '0 0 12px var(--accent-glow)' : 'none',
                }}
              >
                <span>{emoji}</span> {label}
              </button>
            );
          })}
        </div>

        {/* Custom interest */}
        <div style={{ display: 'flex', gap: '8px' }}>
          <input
            id="custom-interest" type="text"
            value={customInterest}
            onChange={e => setCustomInterest(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addCustomInterest(); } }}
            disabled={loading}
            placeholder="Add custom interest…"
            maxLength={50}
            style={{ ...fieldStyle(false), flex: 1 }}
            onFocus={handleFocus}
            onBlur={e => handleBlur(e, false)}
            aria-label="Add custom interest"
          />
          <button
            type="button" onClick={addCustomInterest}
            disabled={loading || !customInterest.trim()}
            style={{
              padding: '10px 14px', borderRadius: '10px',
              background: 'var(--bg-surface)', border: '1px solid var(--accent-border)',
              color: 'var(--accent)', cursor: 'pointer',
              opacity: loading || !customInterest.trim() ? 0.4 : 1,
              transition: 'all 0.15s',
            }}
          >
            <Plus size={16} />
          </button>
        </div>

        {/* Custom tags */}
        {selectedInterests.filter(i => !PRESET_INTERESTS.map(p => p.label.toLowerCase()).includes(i)).length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '10px' }}>
            {selectedInterests
              .filter(i => !PRESET_INTERESTS.map(p => p.label.toLowerCase()).includes(i))
              .map(i => (
                <span key={i} style={{
                  display: 'flex', alignItems: 'center', gap: '6px',
                  padding: '4px 10px', borderRadius: '99px',
                  background: 'var(--bg-surface)', border: '1px solid var(--border)',
                  fontSize: '12px', fontWeight: 500, color: 'var(--text-secondary)',
                }}>
                  {i}
                  <button
                    type="button" onClick={() => removeInterest(i)} disabled={loading}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 0, lineHeight: 1 }}
                  >
                    <X size={12} />
                  </button>
                </span>
              ))}
          </div>
        )}

        {formErrors.interests && (
          <p style={{ fontSize: '11px', color: '#f87171', marginTop: '6px' }}>{formErrors.interests}</p>
        )}
      </div>

      {/* Submit */}
      <button
        id="generate-trip-btn"
        type="submit"
        disabled={loading}
        style={{
          width: '100%',
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px',
          padding: '14px 24px',
          borderRadius: '12px',
          background: loading ? 'var(--accent-dim)' : 'var(--accent)',
          border: '1px solid var(--accent)',
          color: '#000',
          fontSize: '15px', fontWeight: 800,
          cursor: loading ? 'not-allowed' : 'pointer',
          opacity: loading ? 0.75 : 1,
          transition: 'all 0.15s',
          boxShadow: loading ? 'none' : '0 0 28px var(--accent-glow)',
          letterSpacing: '-0.01em',
        }}
        onMouseEnter={e => { if (!loading) (e.currentTarget as HTMLElement).style.boxShadow = '0 0 40px rgba(34,197,94,0.45)'; }}
        onMouseLeave={e => { if (!loading) (e.currentTarget as HTMLElement).style.boxShadow = '0 0 28px var(--accent-glow)'; }}
      >
        {loading ? (
          <>
            <LoadingSpinner size="sm" />
            Sending to AI agents…
          </>
        ) : (
          <>
            <span>✈️</span>
            Generate My Trip
          </>
        )}
      </button>
    </form>
  );
}
