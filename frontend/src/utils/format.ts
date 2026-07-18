/**
 * Utility formatting helpers — no business logic, pure display helpers.
 */

/** Format a currency number to a human-readable string */
export function formatCurrency(amount: number, currency = 'USD'): string {
  try {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  } catch {
    return `${currency} ${amount.toLocaleString()}`;
  }
}

/** Format an ISO date string to a readable date, e.g. "July 18, 2026" */
export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '—';
  try {
    // Handle both "YYYY-MM-DD" and full ISO datetime strings
    const d = new Date(dateStr.length === 10 ? `${dateStr}T12:00:00Z` : dateStr);
    return d.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      timeZone: 'UTC',
    });
  } catch {
    return dateStr;
  }
}

/** Format duration in minutes to a compact string: "2h 30m" */
export function formatDuration(minutes: number): string {
  if (minutes <= 0) return '';
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m}m`;
  if (m === 0) return `${h}h`;
  return `${h}h ${m}m`;
}

/** Truncate a string at a word boundary */
export function truncate(str: string, maxLength = 120): string {
  if (str.length <= maxLength) return str;
  const trimmed = str.slice(0, maxLength);
  const lastSpace = trimmed.lastIndexOf(' ');
  return (lastSpace > 0 ? trimmed.slice(0, lastSpace) : trimmed) + '…';
}

/** Get a short date range string: "Jul 18 – Jul 22, 2026" */
export function formatDateRange(startDate: string, endDate: string): string {
  try {
    const start = new Date(`${startDate}T12:00:00Z`);
    const end = new Date(`${endDate}T12:00:00Z`);
    const opts: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric', timeZone: 'UTC' };
    const yearOpts: Intl.DateTimeFormatOptions = { ...opts, year: 'numeric' };
    return `${start.toLocaleDateString('en-US', opts)} – ${end.toLocaleDateString('en-US', yearOpts)}`;
  } catch {
    return `${startDate} – ${endDate}`;
  }
}

/** Capitalize the first letter of a string */
export function capitalize(str: string): string {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1);
}
