import { Link, Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { getToken, setToken } from "../modules/shared/api";
import { LoginPage, RegisterPage } from "../modules/auth/AuthPages";
import { AthleteDashboard } from "../modules/athlete/AthleteDashboard";
import { CoachDashboard } from "../modules/coach/CoachDashboard";

function RequireAuth({ children }: { children: React.ReactNode }) {
  if (!getToken()) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function AppLayout() {
  const location = useLocation();

  function logout() {
    setToken(null);
    window.location.href = "/login";
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <strong>Coach App</strong>
        <nav>
          <Link to="/athlete" className={location.pathname.startsWith("/athlete") ? "active" : ""}>
            Athlete
          </Link>
          <Link to="/coach" className={location.pathname.startsWith("/coach") ? "active" : ""}>
            Coach
          </Link>
          <button type="button" className="secondary" onClick={logout}>
            Log out
          </button>
        </nav>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route path="/" element={<Navigate to="/athlete" replace />} />
        <Route path="/athlete" element={<AthleteDashboard />} />
        <Route path="/coach" element={<CoachDashboard />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
