import { useAuth } from "../auth/AuthContext";
import { RecoveryForm } from "./recovery/RecoveryForm";
import { TodayWorkoutCard } from "./TodayWorkoutCard";

export function TodaySummary() {
  const { user } = useAuth();

  return (
    <section className="stack today-summary">
      <div className="row-between">
        <div>
          <h1>Athlete dashboard</h1>
          {user && (
            <p className="muted">
              Welcome back, <strong>{user.name}</strong>
            </p>
          )}
        </div>
        {user && (
          <span className={`badge ${user.strava_connected ? "badge-ok" : "badge-muted"}`}>
            Strava {user.strava_connected ? "connected" : "not connected"}
          </span>
        )}
      </div>

      <div className="today-grid">
        <div className="card stack">
          <TodayWorkoutCard />
        </div>
        <div className="card">
          <RecoveryForm />
        </div>
      </div>
    </section>
  );
}
