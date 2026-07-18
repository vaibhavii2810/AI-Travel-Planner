import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles, Zap, Shield, RotateCcw, ArrowRight, Globe2, CloudSun } from 'lucide-react';
import { TravelRequestForm } from '@/components/TravelRequestForm';
import { Navbar } from '@/components/Navbar';
import { createPlan } from '@/api/client';
import type { ApiError } from '@/api/client';
import type { CreatePlanRequest } from '@/types/api';

const FEATURES = [
  { icon: Globe2,    label: 'Real-time Research',        desc: 'Live web + weather data for your destination' },
  { icon: Sparkles,  label: 'AI Itinerary Builder',      desc: 'Day-by-day plans tailored to your interests' },
  { icon: Shield,    label: 'Human-in-the-Loop',         desc: 'You review, revise, or approve before we finalise' },
  { icon: RotateCcw, label: 'Unlimited Revisions',       desc: 'Not happy? Reject with feedback and we\'ll redo it' },
  { icon: CloudSun,  label: 'Weather-Aware Planning',    desc: 'Activities adjusted for real seasonal conditions' },
  { icon: Zap,       label: 'LangGraph Orchestration',   desc: 'Powered by a multi-agent AI state machine' },
];

export function HomePage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { localStorage.removeItem('activePlanId'); }, []);

  const handleSubmit = async (req: CreatePlanRequest) => {
    setLoading(true);
    setError(null);
    try {
      const res = await createPlan(req);
      localStorage.setItem('activePlanId', res.plan_id);
      navigate(`/plan/${res.plan_id}`);
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr.message ?? 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)' }}>
      <Navbar />

      <main style={{ maxWidth: '1200px', margin: '0 auto', padding: '48px 24px 80px' }}>

        {/* ── Hero ───────────────────────────────────────────────────── */}
        <div style={{ textAlign: 'center', marginBottom: '56px' }} className="animate-fade-in">



          <h1 style={{
            fontFamily: "'Space Grotesk', sans-serif",
            fontWeight: 800,
            fontSize: 'clamp(36px, 6vw, 64px)',
            lineHeight: 1.1,
            letterSpacing: '-0.03em',
            marginBottom: '20px',
          }}>
            Plan smarter trips,{' '}
            <span className="text-gradient">effortlessly.</span>
          </h1>

          <p style={{
            fontSize: '18px',
            color: 'var(--text-secondary)',
            maxWidth: '520px',
            margin: '0 auto 36px',
            lineHeight: 1.7,
          }}>
            Tell us where you want to go and what you love doing.
            Our AI agents handle the research, planning, and budgeting — you just review and approve.
          </p>

          {/* How it works inline steps */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexWrap: 'wrap', gap: '6px',
            marginBottom: '0',
          }}>
            {['Submit request', 'AI researches', 'Plan generated', 'You review', 'Final itinerary'].map((step, i, arr) => (
              <div key={step} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{
                  display: 'inline-flex', alignItems: 'center', gap: '6px',
                  padding: '5px 12px',
                  borderRadius: '99px',
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border)',
                  fontSize: '12px',
                  fontWeight: 500,
                  color: 'var(--text-secondary)',
                }}>
                  <span style={{
                    width: '18px', height: '18px', borderRadius: '50%',
                    background: i === arr.length - 1 ? 'var(--accent)' : 'var(--bg-surface)',
                    border: '1px solid var(--accent-border)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: '10px', fontWeight: 700,
                    color: i === arr.length - 1 ? '#000' : 'var(--accent)',
                    flexShrink: 0,
                  }}>{i + 1}</span>
                  {step}
                </span>
                {i < arr.length - 1 && <ArrowRight size={12} color="var(--text-muted)" />}
              </div>
            ))}
          </div>
        </div>

        {/* ── Two-column layout ──────────────────────────────────────── */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: '28px', alignItems: 'start' }}>

          {/* Form card */}
          <div style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
            borderRadius: '18px',
            padding: '32px',
            boxShadow: 'var(--shadow-card)',
          }} className="animate-slide-up">
            <div style={{ marginBottom: '24px' }}>
              <h2 style={{
                fontFamily: "'Space Grotesk', sans-serif",
                fontWeight: 700, fontSize: '20px',
                color: 'var(--text-primary)',
                marginBottom: '6px',
              }}>
                Build your trip
              </h2>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                Fill in the details below and let our agents do the heavy lifting.
              </p>
            </div>

            <TravelRequestForm onSubmit={handleSubmit} loading={loading} error={error} />
          </div>

          {/* Sidebar */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }} className="animate-slide-up">

            {/* Feature list */}
            <div style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: '16px',
              padding: '20px',
            }}>
              <p style={{
                fontSize: '11px', fontWeight: 700, letterSpacing: '0.08em',
                textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '16px',
              }}>
                What's included
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {FEATURES.map(({ icon: Icon, label, desc }) => (
                  <div key={label} style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                    <div style={{
                      width: '32px', height: '32px', borderRadius: '8px',
                      background: 'var(--accent-glow)',
                      border: '1px solid var(--accent-border)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      flexShrink: 0,
                    }}>
                      <Icon size={14} color="var(--accent)" />
                    </div>
                    <div>
                      <p style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '2px' }}>{label}</p>
                      <p style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: 1.5 }}>{desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Accent info box */}
            <div style={{
              background: 'linear-gradient(135deg, rgba(34,197,94,0.12) 0%, rgba(34,197,94,0.04) 100%)',
              border: '1px solid var(--accent-border)',
              borderRadius: '16px',
              padding: '18px',
            }}>
              <p style={{ fontSize: '13px', fontWeight: 700, color: 'var(--accent)', marginBottom: '6px' }}>
                🤖 Running locally?
              </p>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                When no OpenAI key is set, the system uses intelligent mock agents that still produce
                fully personalised, unique itineraries for each interest and destination you enter.
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
