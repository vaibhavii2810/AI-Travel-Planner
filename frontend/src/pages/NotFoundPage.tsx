import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
      <div className="text-center">
        <p className="text-6xl mb-4" aria-hidden="true">🗺️</p>
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Page Not Found</h1>
        <p className="text-slate-500 mb-6">We couldn't find what you were looking for.</p>
        <Link
          to="/"
          className="inline-flex items-center px-5 py-2.5 bg-brand-600 text-white font-semibold rounded-xl hover:bg-brand-700 transition-colors"
        >
          Back to Home
        </Link>
      </div>
    </div>
  );
}
