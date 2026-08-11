import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { getToken } from "../modules/shared/api";
import { LoginPage, RegisterPage } from "../modules/auth/AuthPages";
import { useAuth } from "../modules/auth/AuthContext";
import { defaultHomePath } from "../modules/auth/roles";
import type { UserRole } from "../modules/shared/api";
import { AthleteProfilePage } from "../modules/athlete-profile/AthleteProfilePage";
import { ActivitiesPage, AthleteSettingsPage } from "../modules/athlete/ActivitiesPage";
import { StravaOAuthPage } from "../modules/athlete/strava/StravaOAuthPage";
import { CoachDashboard } from "../modules/coach/CoachDashboard";
import { CoachActivitiesPage } from "../modules/coach/CoachActivitiesPage";
import { AthleteWorkspaceLayout } from "../modules/coach/athlete/AthleteWorkspaceLayout";
import { AthleteOverviewPage } from "../modules/coach/athlete/AthleteOverviewPage";
import { AthletePlanPage } from "../modules/coach/athlete/AthletePlanPage";
import { AthleteActivitiesPage } from "../modules/coach/athlete/AthleteActivitiesPage";
import { AthletePerformancePage } from "../modules/coach/athlete/AthletePerformancePage";
import { AthleteRecoveryPage } from "../modules/coach/athlete/AthleteRecoveryPage";
import { PlanningHubPage } from "../modules/coach/PlanningHubPage";
import { TemplatesPage } from "../modules/coach/TemplatesPage";
import {
  EditWorkoutBuilderPage,
  NewWorkoutBuilderPage,
  TemplateBuilderPage,
} from "../modules/workout/builder/CoachWorkoutBuilderPage";
import { TodayPage } from "../modules/today/TodayPage";
import { ActivityDetailsPage } from "../modules/activities/ActivityDetailsPage";
import { AppLayout } from "../modules/shell/AppLayout";
import { ComingSoonPage } from "../modules/shell/ComingSoonPage";

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

function ActivitiesOrComingSoon() {
  const { hasRole } = useAuth();
  if (hasRole("athlete")) return <ActivitiesPage />;
  if (hasRole("coach")) return <CoachActivitiesPage />;
  return <Navigate to="/today" replace />;
}

function AuthenticatedShell() {
  return (
    <RequireAuth>
      <AppLayout>
        <Outlet />
      </AppLayout>
    </RequireAuth>
  );
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<AuthenticatedShell />}>
        <Route path="/" element={<RoleRedirect />} />
        <Route path="/today" element={<TodayPage />} />
        <Route path="/activity/:activityId" element={<ActivityDetailsPage />} />

        <Route path="/athlete" element={<Navigate to="/today" replace />} />
        <Route path="/coach" element={<Navigate to="/today" replace />} />

        <Route
          path="/activities"
          element={<ActivitiesOrComingSoon />}
        />
        <Route
          path="/settings"
          element={
            <RequireRole role="athlete">
              <AthleteSettingsPage />
            </RequireRole>
          }
        />
        <Route
          path="/athlete/profile"
          element={
            <RequireRole role="athlete">
              <AthleteProfilePage />
            </RequireRole>
          }
        />
        <Route
          path="/performance"
          element={
            <RequireRole role="athlete">
              <Navigate to="/athlete/profile" replace />
            </RequireRole>
          }
        />
        <Route
          path="/plan"
          element={
            <RequireRole role="athlete">
              <ComingSoonPage title="Plan" />
            </RequireRole>
          }
        />
        <Route
          path="/recovery"
          element={
            <RequireRole role="athlete">
              <ComingSoonPage title="Recovery" />
            </RequireRole>
          }
        />
        <Route
          path="/athletes"
          element={
            <RequireRole role="coach">
              <CoachDashboard />
            </RequireRole>
          }
        />
        <Route
          path="/coach/athletes/:athleteId"
          element={
            <RequireRole role="coach">
              <AthleteWorkspaceLayout />
            </RequireRole>
          }
        >
          <Route index element={<AthleteOverviewPage />} />
          <Route path="plan" element={<AthletePlanPage />} />
          <Route path="activities" element={<AthleteActivitiesPage />} />
          <Route path="performance" element={<AthletePerformancePage />} />
          <Route path="recovery" element={<AthleteRecoveryPage />} />
        </Route>
        <Route
          path="/planning"
          element={
            <RequireRole role="coach">
              <PlanningHubPage />
            </RequireRole>
          }
        />
        <Route
          path="/planning/workout/new"
          element={
            <RequireRole role="coach">
              <NewWorkoutBuilderPage />
            </RequireRole>
          }
        />
        <Route
          path="/planning/workout/:workoutId"
          element={
            <RequireRole role="coach">
              <EditWorkoutBuilderPage />
            </RequireRole>
          }
        />
        <Route
          path="/analysis"
          element={
            <RequireRole role="coach">
              <ComingSoonPage title="Analysis" />
            </RequireRole>
          }
        />
        <Route
          path="/templates"
          element={
            <RequireRole role="coach">
              <TemplatesPage />
            </RequireRole>
          }
        />
        <Route
          path="/templates/new"
          element={
            <RequireRole role="coach">
              <TemplateBuilderPage />
            </RequireRole>
          }
        />
        <Route
          path="/templates/:templateId/edit"
          element={
            <RequireRole role="coach">
              <TemplateBuilderPage />
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
