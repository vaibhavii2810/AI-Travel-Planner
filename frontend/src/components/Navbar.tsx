import { Link } from 'react-router-dom';
import { Sun, Moon, Compass } from 'lucide-react';
import { useTheme } from '@/App';

interface NavbarProps {
  showBack?: boolean;
  planId?: string;
  onCopyId?: () => void;
  copied?: boolean;
  rightSlot?: React.ReactNode;
}

export function Navbar({ showBack, planId, onCopyId, copied, rightSlot }: NavbarProps) {
  const { theme, toggle } = useTheme();

  return (
    <header
      style={{
        background: 'var(--bg-surface)',
        borderBottom: '1px solid var(--border)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        position: 'sticky',
        top: 0,
        zIndex: 40,
      }}
    >
      <div
        style={{
          maxWidth: '1200px',
          margin: '0 auto',
          padding: '0 24px',
          height: '60px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
        }}
      >
        {/* Left: Logo + optional back */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {showBack && (
            <Link
              to="/new"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                color: 'var(--text-secondary)',
                textDecoration: 'none',
                fontSize: '13px',
                fontWeight: 500,
                transition: 'color 150ms',
                paddingRight: '16px',
                borderRight: '1px solid var(--border)',
              }}
              onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-primary)')}
              onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-secondary)')}
            >
              ← New Plan
            </Link>
          )}

          {/* Logo mark */}
          <Link
            to="/new"
            style={{ display: 'flex', alignItems: 'center', gap: '10px', textDecoration: 'none' }}
          >
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '10px',
                background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 0 14px rgba(34,197,94,0.4)',
                flexShrink: 0,
              }}
            >
              <Compass size={16} color="#000" strokeWidth={2.5} />
            </div>
            <div>
              <div
                style={{
                  fontFamily: "'Space Grotesk', sans-serif",
                  fontWeight: 700,
                  fontSize: '15px',
                  color: 'var(--text-primary)',
                  letterSpacing: '-0.01em',
                  lineHeight: 1.1,
                }}
              >
                VoyageAI
              </div>
              <div
                style={{
                  fontSize: '10px',
                  fontWeight: 500,
                  color: 'var(--accent)',
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                  lineHeight: 1,
                }}
              >
                Smart Trip Planner
              </div>
            </div>
          </Link>
        </div>

        {/* Right: plan id + theme toggle */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {rightSlot}

          {planId && onCopyId && (
            <button
              onClick={onCopyId}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '5px 10px',
                borderRadius: '6px',
                border: '1px solid var(--border)',
                background: 'transparent',
                color: 'var(--text-muted)',
                fontSize: '11px',
                fontFamily: 'monospace',
                cursor: 'pointer',
                transition: 'all 150ms',
              }}
              onMouseEnter={e => {
                (e.currentTarget as HTMLElement).style.color = 'var(--text-secondary)';
                (e.currentTarget as HTMLElement).style.borderColor = 'var(--border-hover)';
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLElement).style.color = 'var(--text-muted)';
                (e.currentTarget as HTMLElement).style.borderColor = 'var(--border)';
              }}
            >
              {copied ? (
                <span style={{ color: 'var(--accent)' }}>✓ Copied</span>
              ) : (
                <span>#{planId.slice(0, 8)}…</span>
              )}
            </button>
          )}

          {/* Dark / Light toggle */}
          <button
            onClick={toggle}
            aria-label="Toggle theme"
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              border: '1px solid var(--border)',
              background: 'var(--bg-card)',
              color: 'var(--text-secondary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              transition: 'all 150ms',
              flexShrink: 0,
            }}
            onMouseEnter={e => {
              (e.currentTarget as HTMLElement).style.borderColor = 'var(--accent-border)';
              (e.currentTarget as HTMLElement).style.color = 'var(--accent)';
            }}
            onMouseLeave={e => {
              (e.currentTarget as HTMLElement).style.borderColor = 'var(--border)';
              (e.currentTarget as HTMLElement).style.color = 'var(--text-secondary)';
            }}
          >
            {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
          </button>
        </div>
      </div>
    </header>
  );
}
