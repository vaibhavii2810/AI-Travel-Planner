export function LoadingSkeleton({ className = '' }: { className?: string }) {
  return (
    <div
      className={`bg-slate-100 rounded-lg animate-pulse ${className}`}
      aria-hidden="true"
    />
  );
}

export function ItinerarySkeleton() {
  return (
    <div className="space-y-6 animate-fade-in" aria-label="Loading itinerary…">
      {[1, 2, 3].map((i) => (
        <div key={i} className="bg-white rounded-2xl border border-slate-100 shadow-card p-6 space-y-4">
          <LoadingSkeleton className="h-5 w-32" />
          <LoadingSkeleton className="h-4 w-24" />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
            {['Morning', 'Afternoon', 'Evening'].map((slot) => (
              <div key={slot} className="space-y-2">
                <LoadingSkeleton className="h-3 w-16" />
                <LoadingSkeleton className="h-20 w-full" />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export function PlanSummarySkeleton() {
  return (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-card p-6 space-y-4 animate-pulse">
      <LoadingSkeleton className="h-6 w-48" />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="space-y-1">
            <LoadingSkeleton className="h-3 w-16" />
            <LoadingSkeleton className="h-5 w-24" />
          </div>
        ))}
      </div>
    </div>
  );
}
