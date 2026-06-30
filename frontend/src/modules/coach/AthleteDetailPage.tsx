import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getAthlete, type CoachAthleteDetail } from "../coaching/api";
import { formatDate } from "../shared/dates";
import { CoachAthleteProfileSection } from "./CoachAthleteProfileSection";
import { AthleteTodayRecoverySection } from "./AthleteTodayRecoverySection";
import { CoachMonthCalendar } from "./calendar/CoachMonthCalendar";
import { CreateWorkoutForm } from "./CreateWorkoutForm";

export function AthleteDetailPage() {
  const { athleteId } = useParams<{ athleteId: string }>();
  const id = Number(athleteId);
  const [detail, setDetail] = useState<CoachAthleteDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [calendarRefreshKey, setCalendarRefreshKey] = useState(0);

  useEffect(() => {
    if (!id || Number.isNaN(id)) {
      setError("Invalid athlete");
      setLoading(false);
      return;
    }
    getAthlete(id).then((result) => {
      if (!result.success || !result.athlete) {
        setError(result.error ?? "Failed to load athlete");
      } else {
        setDetail({
          relation_id: result.relation_id,
          coaching_since: result.coaching_since,
          athlete: result.athlete,
          upcoming_workouts_count: result.upcoming_workouts_count ?? 0,
        });
      }
      setLoading(false);
    });
  }, [id]);

  if (loading) return <p className="muted">Loading athlete…</p>;
  if (error || !detail) return <p className="error">{error ?? "Athlete not found"}</p>;

  const { athlete } = detail;

  return (
    <div className="stack">
      <p>
        <Link to="/coach">← Back to athletes</Link>
      </p>

      <div className="card stack">
        <h1>{athlete.name}</h1>
        <p className="muted">
          @{athlete.username} · {athlete.email}
        </p>
        {detail.coaching_since && (
          <p className="muted">
            Coaching since {formatDate(detail.coaching_since.slice(0, 10))}
          </p>
        )}
        <p>
          <span className="badge badge-ok">{detail.upcoming_workouts_count} upcoming</span>{" "}
          <span className="muted">in the next 7 days</span>
        </p>
      </div>

      <AthleteTodayRecoverySection athleteId={athlete.id} />

      <CoachAthleteProfileSection athleteId={athlete.id} />

      <CreateWorkoutForm
        athleteId={athlete.id}
        onCreated={() => setCalendarRefreshKey((k) => k + 1)}
      />

      <CoachMonthCalendar athleteId={athlete.id} refreshKey={calendarRefreshKey} />
    </div>
  );
}
