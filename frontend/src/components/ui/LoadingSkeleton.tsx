function Bone({ w = '100%', h = 14, r = 6, mb = 0 }: { w?: string | number; h?: number; r?: number; mb?: number }) {
  return (
    <div className="skeleton" style={{ width: w, height: h, borderRadius: r, marginBottom: mb }} />
  );
}

export function PlanSummarySkeleton() {
  return (
    <div style={{
      background: 'var(--bg-card)', border: '1px solid var(--border)',
      borderRadius: '16px', padding: '20px 24px',
    }}>
      <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
        <Bone w={40} h={40} r={10} />
        <div style={{ flex: 1 }}>
          <Bone w="55%" h={18} r={6} mb={8} />
          <Bone w="35%" h={12} r={4} />
        </div>
        <Bone w={90} h={32} r={8} />
      </div>
    </div>
  );
}

export function ItinerarySkeleton() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {[1, 2, 3].map(i => (
        <div key={i} style={{
          background: 'var(--bg-card)', border: '1px solid var(--border)',
          borderRadius: '16px', padding: '20px 24px',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px' }}>
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              <Bone w={36} h={36} r={10} />
              <div>
                <Bone w={80} h={16} r={4} mb={6} />
                <Bone w={120} h={11} r={3} />
              </div>
            </div>
            <Bone w={80} h={36} r={8} />
          </div>
          <Bone w="40%" h={11} r={3} mb={10} />
          <Bone h={60} r={10} mb={16} />
          <Bone w="40%" h={11} r={3} mb={10} />
          <Bone h={60} r={10} mb={16} />
          <Bone w="40%" h={11} r={3} mb={10} />
          <Bone h={60} r={10} />
        </div>
      ))}
    </div>
  );
}
