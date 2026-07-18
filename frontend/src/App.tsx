import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { HomePage } from '@/pages/HomePage';
import { PlanPage } from '@/pages/PlanPage';
import { NotFoundPage } from '@/pages/NotFoundPage';
import { ThemeProvider } from '@/components/ThemeProvider';

// ── App ────────────────────────────────────────────────────────────────────────
function App() {
  const storedPlanId = localStorage.getItem('activePlanId');
  return (
    <ThemeProvider>
      <BrowserRouter>
        <Routes>
          <Route
            path="/"
            element={storedPlanId ? <Navigate to={`/plan/${storedPlanId}`} replace /> : <HomePage />}
          />
          <Route path="/plan/:planId" element={<PlanPage />} />
          <Route path="/new" element={<HomePage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
