import { useState } from 'react';
import { MapPin, Calendar, DollarSign, Users, Plus, X } from 'lucide-react';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import type { CreatePlanRequest } from '@/types/api';

const PRESET_INTERESTS = [
  { label: 'Adventure',   emoji: '🏔️' },
  { label: 'Food',        emoji: '🍜' },
  { label: 'Culture',     emoji: '🎭' },
  { label: 'History',     emoji: '🏛️' },
  { label: 'Nature',      emoji: '🌿' },
  { label: 'Beaches',     emoji: '🏖️' },
  { label: 'Nightlife',   emoji: '🎉' },
  { label: 'Shopping',    emoji: '🛍️' },
  { label: 'Relaxation',  emoji: '🧘' },
];

// Helper — today's date as "YYYY-MM-DD"
function todayStr(): string {
  return new Date().toISOString().slice(0, 10);
}

function tomorrowStr(): string {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  return d.toISOString().slice(0, 10);
}

interface TravelRequestFormProps {
  onSubmit: (req: CreatePlanRequest) => Promise<void>;
  loading: boolean;
  error?: string | null;
}

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
    setSelectedInterests((prev) =>
      prev.includes(label.toLowerCase())
        ? prev.filter((i) => i !== label.toLowerCase())
        : [...prev, label.toLowerCase()],
    );
  };

  const addCustomInterest = () => {
    const val = customInterest.trim().toLowerCase();
    if (val && !selectedInterests.includes(val)) {
      setSelectedInterests((prev) => [...prev, val]);
    }
    setCustomInterest('');
  };

  const removeInterest = (interest: string) => {
    setSelectedInterests((prev) => prev.filter((i) => i !== interest));
  };

  const validate = (): boolean => {
    const errors: Record<string, string> = {};

    if (!destination.trim() || destination.trim().length < 2) {
      errors.destination = 'Destination must be at least 2 characters.';
    }
    if (!startDate) errors.startDate = 'Start date is required.';
    if (!endDate) errors.endDate = 'End date is required.';
    if (startDate && endDate && endDate <= startDate) {
      errors.endDate = 'End date must be after start date.';
    }
    const min = parseFloat(budgetMin);
    const max = parseFloat(budgetMax);
    if (!budgetMin || isNaN(min) || min <= 0) {
      errors.budgetMin = 'Minimum budget must be greater than 0.';
    }
    if (!budgetMax || isNaN(max) || max <= 0) {
      errors.budgetMax = 'Maximum budget must be greater than 0.';
    }
    if (!isNaN(min) && !isNaN(max) && max < min) {
      errors.budgetMax = 'Maximum budget must be ≥ minimum budget.';
    }
    const t = parseInt(travelers, 10);
    if (isNaN(t) || t < 1 || t > 50) {
      errors.travelers = 'Number of travelers must be between 1 and 50.';
    }
    if (selectedInterests.length === 0) {
      errors.interests = 'Please select at least one interest.';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    const req: CreatePlanRequest = {
      destination: destination.trim(),
      start_date: startDate,
      end_date: endDate,
      budget_min: parseFloat(budgetMin),
      budget_max: parseFloat(budgetMax),
      budget_currency: currency,
      num_travelers: parseInt(travelers, 10),
      interests: selectedInterests,
    };

    await onSubmit(req);
  };

  const fieldClass = (key: string) =>
    `w-full px-4 py-3 rounded-xl border text-sm text-slate-800 placeholder-slate-400 bg-white focus:outline-none focus:ring-2 focus:ring-brand-500 transition-colors ${
      formErrors[key] ? 'border-red-300 bg-red-50' : 'border-slate-200 hover:border-slate-300'
    }`;

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-6" aria-label="Travel request form">
      {/* Global API error */}
      {error && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-sm text-red-700" role="alert">
          <span className="font-semibold">Error: </span>{error}
        </div>
      )}

      {/* Destination */}
      <div>
        <label htmlFor="destination" className="block text-sm font-semibold text-slate-700 mb-1.5">
          <MapPin className="inline w-4 h-4 mr-1 text-brand-500" aria-hidden="true" />
          Destination
        </label>
        <input
          id="destination"
          type="text"
          value={destination}
          onChange={(e) => setDestination(e.target.value)}
          disabled={loading}
          placeholder="e.g. Kyoto, Japan"
          maxLength={200}
          autoComplete="off"
          className={fieldClass('destination')}
        />
        {formErrors.destination && (
          <p className="text-xs text-red-500 mt-1">{formErrors.destination}</p>
        )}
      </div>

      {/* Dates */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label htmlFor="start-date" className="block text-sm font-semibold text-slate-700 mb-1.5">
            <Calendar className="inline w-4 h-4 mr-1 text-brand-500" aria-hidden="true" />
            Start Date
          </label>
          <input
            id="start-date"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            disabled={loading}
            min={todayStr()}
            className={fieldClass('startDate')}
          />
          {formErrors.startDate && (
            <p className="text-xs text-red-500 mt-1">{formErrors.startDate}</p>
          )}
        </div>
        <div>
          <label htmlFor="end-date" className="block text-sm font-semibold text-slate-700 mb-1.5">
            <Calendar className="inline w-4 h-4 mr-1 text-brand-500" aria-hidden="true" />
            End Date
          </label>
          <input
            id="end-date"
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            disabled={loading}
            min={startDate || tomorrowStr()}
            className={fieldClass('endDate')}
          />
          {formErrors.endDate && (
            <p className="text-xs text-red-500 mt-1">{formErrors.endDate}</p>
          )}
        </div>
      </div>

      {/* Budget */}
      <div>
        <p className="text-sm font-semibold text-slate-700 mb-1.5">
          <DollarSign className="inline w-4 h-4 mr-1 text-brand-500" aria-hidden="true" />
          Budget Range
        </p>
        <div className="grid grid-cols-3 gap-3">
          {/* Currency */}
          <div>
            <label htmlFor="currency" className="block text-xs text-slate-500 mb-1">Currency</label>
            <select
              id="currency"
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              disabled={loading}
              className={`${fieldClass('currency')} pr-8`}
            >
              {['USD', 'EUR', 'GBP', 'INR', 'JPY', 'AUD', 'CAD'].map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          {/* Min */}
          <div>
            <label htmlFor="budget-min" className="block text-xs text-slate-500 mb-1">Minimum</label>
            <input
              id="budget-min"
              type="number"
              value={budgetMin}
              onChange={(e) => setBudgetMin(e.target.value)}
              disabled={loading}
              min="1"
              step="any"
              placeholder="500"
              className={fieldClass('budgetMin')}
            />
            {formErrors.budgetMin && (
              <p className="text-xs text-red-500 mt-1">{formErrors.budgetMin}</p>
            )}
          </div>
          {/* Max */}
          <div>
            <label htmlFor="budget-max" className="block text-xs text-slate-500 mb-1">Maximum</label>
            <input
              id="budget-max"
              type="number"
              value={budgetMax}
              onChange={(e) => setBudgetMax(e.target.value)}
              disabled={loading}
              min="1"
              step="any"
              placeholder="2000"
              className={fieldClass('budgetMax')}
            />
            {formErrors.budgetMax && (
              <p className="text-xs text-red-500 mt-1">{formErrors.budgetMax}</p>
            )}
          </div>
        </div>
      </div>

      {/* Travelers */}
      <div>
        <label htmlFor="travelers" className="block text-sm font-semibold text-slate-700 mb-1.5">
          <Users className="inline w-4 h-4 mr-1 text-brand-500" aria-hidden="true" />
          Number of Travelers
        </label>
        <input
          id="travelers"
          type="number"
          value={travelers}
          onChange={(e) => setTravelers(e.target.value)}
          disabled={loading}
          min="1"
          max="50"
          className={`${fieldClass('travelers')} max-w-[140px]`}
        />
        {formErrors.travelers && (
          <p className="text-xs text-red-500 mt-1">{formErrors.travelers}</p>
        )}
      </div>

      {/* Interests */}
      <div>
        <p className="text-sm font-semibold text-slate-700 mb-2">
          Interests &amp; Preferences
          <span className="ml-1 text-xs text-slate-400 font-normal">(select all that apply)</span>
        </p>

        {/* Preset chips */}
        <div className="flex flex-wrap gap-2 mb-3" role="group" aria-label="Interest options">
          {PRESET_INTERESTS.map(({ label, emoji }) => {
            const val = label.toLowerCase();
            const selected = selectedInterests.includes(val);
            return (
              <button
                key={label}
                type="button"
                onClick={() => toggleInterest(label)}
                disabled={loading}
                aria-pressed={selected}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-1 ${
                  selected
                    ? 'bg-brand-600 text-white border-brand-600 shadow-sm'
                    : 'bg-white text-slate-600 border-slate-200 hover:border-brand-300 hover:text-brand-700'
                }`}
              >
                <span aria-hidden="true">{emoji}</span>
                {label}
              </button>
            );
          })}
        </div>

        {/* Custom interest input */}
        <div className="flex gap-2">
          <input
            id="custom-interest"
            type="text"
            value={customInterest}
            onChange={(e) => setCustomInterest(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                addCustomInterest();
              }
            }}
            disabled={loading}
            placeholder="Add custom interest…"
            maxLength={50}
            className="flex-1 px-3 py-2 rounded-xl border border-slate-200 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500 hover:border-slate-300"
            aria-label="Add custom interest"
          />
          <button
            type="button"
            onClick={addCustomInterest}
            disabled={loading || !customInterest.trim()}
            className="px-3 py-2 rounded-xl border border-brand-200 text-brand-600 hover:bg-brand-50 disabled:opacity-40 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500"
            aria-label="Add custom interest"
          >
            <Plus className="w-4 h-4" aria-hidden="true" />
          </button>
        </div>

        {/* Custom interest chips */}
        {selectedInterests.filter(
          (i) => !PRESET_INTERESTS.map((p) => p.label.toLowerCase()).includes(i),
        ).length > 0 && (
          <div className="flex flex-wrap gap-2 mt-2">
            {selectedInterests
              .filter((i) => !PRESET_INTERESTS.map((p) => p.label.toLowerCase()).includes(i))
              .map((i) => (
                <span
                  key={i}
                  className="flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200"
                >
                  {i}
                  <button
                    type="button"
                    onClick={() => removeInterest(i)}
                    disabled={loading}
                    className="hover:text-red-500 transition-colors focus:outline-none"
                    aria-label={`Remove ${i}`}
                  >
                    <X className="w-3 h-3" aria-hidden="true" />
                  </button>
                </span>
              ))}
          </div>
        )}

        {formErrors.interests && (
          <p className="text-xs text-red-500 mt-1">{formErrors.interests}</p>
        )}
      </div>

      {/* Submit */}
      <button
        id="generate-trip-btn"
        type="submit"
        disabled={loading}
        className="w-full flex items-center justify-center gap-3 px-6 py-4 bg-brand-600 text-white text-base font-bold rounded-xl hover:bg-brand-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 shadow-sm"
      >
        {loading ? (
          <>
            <LoadingSpinner size="md" className="text-white" />
            Sending to AI agents…
          </>
        ) : (
          <>
            <span aria-hidden="true">✈️</span>
            Generate My Trip
          </>
        )}
      </button>
    </form>
  );
}
