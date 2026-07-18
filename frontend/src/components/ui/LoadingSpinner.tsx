interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  style?: React.CSSProperties;
}

const SIZE_MAP = { sm: 16, md: 24, lg: 36 };

export function LoadingSpinner({ size = 'md', style }: LoadingSpinnerProps) {
  const px = SIZE_MAP[size];
  return (
    <div
      style={{
        width: px, height: px,
        borderRadius: '50%',
        border: `${size === 'lg' ? 3 : 2}px solid var(--border)`,
        borderTopColor: 'var(--accent)',
        animation: 'spin 0.8s linear infinite',
        display: 'inline-block',
        flexShrink: 0,
        ...style,
      }}
      role="status"
      aria-label="Loading"
    />
  );
}
