import { AlertCircle, RefreshCw, WifiOff } from 'lucide-react';
import type { ApiError } from '@/api/client';

interface ErrorStateProps {
  error: ApiError | string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({ error, onRetry, className = '' }: ErrorStateProps) {
  const message = typeof error === 'string' ? error : error.message;
  const status = typeof error === 'string' ? 0 : error.status;

  const isNetworkError = status === 0;
  const Icon = isNetworkError ? WifiOff : AlertCircle;

  return (
    <div className={`flex flex-col items-center justify-center text-center py-12 px-6 ${className}`}>
      <div className="w-14 h-14 rounded-full bg-red-50 flex items-center justify-center mb-4">
        <Icon className="w-7 h-7 text-red-500" aria-hidden="true" />
      </div>
      <h3 className="text-lg font-semibold text-slate-800 mb-2">
        {isNetworkError ? 'Connection Error' : 'Something went wrong'}
      </h3>
      <p className="text-sm text-slate-500 max-w-sm mb-6 leading-relaxed">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded-xl hover:bg-brand-700 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
        >
          <RefreshCw className="w-4 h-4" aria-hidden="true" />
          Try again
        </button>
      )}
    </div>
  );
}
