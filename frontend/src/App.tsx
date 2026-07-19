import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { HomePage } from '@/pages/HomePage';
import { PlanPage } from '@/pages/PlanPage';
import { NotFoundPage } from '@/pages/NotFoundPage';
import { ThemeProvider } from '@/components/ThemeProvider';

// Reads localStorage fresh on every render of the "/" route, instead of once
// at App's initial mount. A plain ternary in App's render body would freeze
// this decision for the app's whole lifetime — so once PlanPage clears a
// stale activePlanId and navigates back to "/", the frozen decision would
// just redirect straight back to the same dead /plan/:id and loop forever.
function RootRedirect() {
  const storedPlanId = localStorage.getItem('activePlanId');
  return storedPlanId ? <Navigate to={`/plan/${storedPlanId}`} replace /> : <HomePage />;
}

// ── App ────────────────────────────────────────────────────────────────────────
function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<RootRedirect />} />
          <Route path="/plan/:planId" element={<PlanPage />} />
          <Route path="/new" element={<HomePage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
