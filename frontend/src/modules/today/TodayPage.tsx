import { useAuth } from "../auth/AuthContext";
import { AthleteTodayPage } from "../athlete/today/AthleteTodayPage";
import { CoachTodayPage } from "../coach/today/CoachTodayPage";
import { useViewRole } from "../shell/AppLayout";

/** Role-split Today home. Dual-role users follow the shell role switcher. */
export function TodayPage() {
  const { hasRole } = useAuth();
  const { viewRole } = useViewRole();

  if (hasRole("athlete") && hasRole("coach")) {
    return viewRole === "coach" ? <CoachTodayPage /> : <AthleteTodayPage />;
  }
  if (hasRole("athlete")) return <AthleteTodayPage />;
  if (hasRole("coach")) return <CoachTodayPage />;

  return <p className="muted">No athlete or coach role assigned.</p>;
}
