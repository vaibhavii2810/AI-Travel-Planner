import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles, Cpu, GitBranch } from 'lucide-react';
import { TravelRequestForm } from '@/components/TravelRequestForm';
import { createPlan } from '@/api/client';
import type { ApiError } from '@/api/client';
import type { CreatePlanRequest } from '@/types/api';

export function HomePage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Clear any stored plan so the router doesn't redirect away from /new
  useEffect(() => {
    localStorage.removeItem('activePlanId');
  }, []);

  const handleSubmit = async (req: CreatePlanRequest) => {
    setLoading(true);
    setError(null);
    try {
      const res = await createPlan(req);
      // Store plan_id for refresh recovery
      localStorage.setItem('activePlanId', res.plan_id);
      navigate(`/plan/${res.plan_id}`);
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-brand-50">
      {/* Header */}
      <header className="border-b border-slate-100 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-brand-600 flex items-center justify-center shadow-sm">
              <span className="text-white text-sm" aria-hidden="true">✈️</span>
            </div>
            <span className="font-bold text-slate-900 text-lg">AI Travel Planner</span>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-slate-400 font-medium">
            <Cpu className="w-3.5 h-3.5" aria-hidden="true" />
            Powered by LangGraph
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-12 lg:py-16">
        {/* Hero section */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-brand-50 border border-brand-100 text-brand-700 text-sm font-medium mb-6">
            <Sparkles className="w-4 h-4" aria-hidden="true" />
            Multi-Agent AI Planning
          </div>
          <h1 className="text-4xl sm:text-5xl font-extrabold text-slate-900 leading-tight mb-4">
            AI Travel Planner
          </h1>
          <p className="text-lg text-slate-500 max-w-xl mx-auto leading-relaxed">
            Plan smarter trips with AI-powered research and personalized itineraries.
          </p>
        </div>

        {/* Feature pills */}
        <div className="flex flex-wrap items-center justify-center gap-3 mb-10">
          {[
            { icon: '🔍', text: 'Real-time research' },
            { icon: '🗺️', text: 'Personalized itineraries' },
            { icon: '✅', text: 'Human-in-the-loop review' },
            { icon: '🔄', text: 'Unlimited revisions' },
          ].map(({ icon, text }) => (
            <div
              key={text}
              className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white border border-slate-200 text-xs text-slate-600 shadow-sm"
            >
              <span aria-hidden="true">{icon}</span>
              {text}
            </div>
          ))}
        </div>

        {/* Layout: Form + Sidebar */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Form panel */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-2xl border border-slate-100 shadow-card p-6 sm:p-8">
              <h2 className="text-xl font-bold text-slate-900 mb-6">Plan Your Trip</h2>
              <TravelRequestForm
                onSubmit={handleSubmit}
                loading={loading}
                error={error}
              />
            </div>
          </div>

          {/* Info sidebar */}
          <aside className="lg:col-span-1 space-y-4">
            <div className="bg-white rounded-2xl border border-slate-100 shadow-card p-5">
              <div className="flex items-center gap-2 mb-3">
                <GitBranch className="w-4 h-4 text-brand-500" aria-hidden="true" />
                <h3 className="text-sm font-bold text-slate-800">How it works</h3>
              </div>
              <ol className="space-y-3 text-sm text-slate-600">
                {[
                  { n: 1, t: 'Submit your travel request' },
                  { n: 2, t: 'AI researches your destination' },
                  { n: 3, t: 'Planner builds a personalized itinerary' },
                  { n: 4, t: 'Review, revise, or approve the plan' },
                  { n: 5, t: 'Download your final itinerary' },
                ].map(({ n, t }) => (
                  <li key={n} className="flex items-start gap-3">
                    <span className="flex-shrink-0 w-5 h-5 rounded-full bg-brand-50 text-brand-600 text-xs font-bold flex items-center justify-center">
                      {n}
                    </span>
                    {t}
                  </li>
                ))}
              </ol>
            </div>

            <div className="bg-brand-600 rounded-2xl p-5 text-white">
              <p className="text-sm font-semibold mb-2">🤖 AI-Powered</p>
              <p className="text-xs leading-relaxed opacity-90">
                Our multi-agent system uses real-time web research, weather data, 
                and intelligent planning to craft your perfect trip.
              </p>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
