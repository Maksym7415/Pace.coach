import { Link, Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { getToken } from "../modules/shared/api";
import { LoginPage, RegisterPage } from "../modules/auth/AuthPages";
import { useAuth } from "../modules/auth/AuthContext";
import { defaultHomePath } from "../modules/auth/roles";
import type { UserRole } from "../modules/shared/api";
import { AthleteDashboard } from "../modules/athlete/AthleteDashboard";
import { StravaOAuthPage } from "../modules/athlete/strava/StravaOAuthPage";
import { CoachDashboard } from "../modules/coach/CoachDashboard";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();

  if (!getToken()) return <Navigate to="/login" replace />;
  if (loading) return <p className="muted">Loading…</p>;
  if (!user) return <Navigate to="/login" replace />;

  return <>{children}</>;
}

function RequireRole({ role, children }: { role: UserRole; children: React.ReactNode }) {
  const { user, hasRole } = useAuth();

  if (!user) return <Navigate to="/login" replace />;
  if (!hasRole(role)) return <Navigate to={defaultHomePath(user.roles)} replace />;

  return <>{children}</>;
}

function RoleRedirect() {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={defaultHomePath(user.roles)} replace />;
}

function AppLayout() {
  const location = useLocation();
  const { hasRole, logout } = useAuth();

  return (
    <div className="app-shell">
      <header className="app-header">
        <strong>Coach App</strong>
        <nav>
          {hasRole("athlete") && (
            <Link to="/athlete" className={location.pathname.startsWith("/athlete") ? "active" : ""}>
              Athlete
            </Link>
          )}
          {hasRole("coach") && (
            <Link to="/coach" className={location.pathname.startsWith("/coach") ? "active" : ""}>
              Coach
            </Link>
          )}
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
        <Route path="/" element={<RoleRedirect />} />
        <Route
          path="/athlete"
          element={
            <RequireRole role="athlete">
              <AthleteDashboard />
            </RequireRole>
          }
        />
        <Route
          path="/coach"
          element={
            <RequireRole role="coach">
              <CoachDashboard />
            </RequireRole>
          }
        />
        <Route
          path="/strava/oauth"
          element={
            <RequireRole role="athlete">
              <StravaOAuthPage />
            </RequireRole>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
