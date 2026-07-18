import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { HomePage } from '@/pages/HomePage';
import { PlanPage } from '@/pages/PlanPage';
import { NotFoundPage } from '@/pages/NotFoundPage';

/**
 * App — top-level router.
 *
 * Routes:
 *   /             → HomePage (travel request form)
 *   /plan/:planId → PlanPage (workflow + HITL + final)
 *   *             → NotFoundPage
 *
 * Refresh recovery: PlanPage reads planId from URL and refetches from backend.
 * localStorage.activePlanId is set on plan creation for convenience redirects.
 */
function App() {
  // Redirect root to an active plan if one exists in localStorage
  const storedPlanId = localStorage.getItem('activePlanId');

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/"
          element={
            storedPlanId ? (
              <Navigate to={`/plan/${storedPlanId}`} replace />
            ) : (
              <HomePage />
            )
          }
        />
        <Route path="/plan/:planId" element={<PlanPage />} />
        <Route path="/new" element={<HomePage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
