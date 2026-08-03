import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { listActivities, type Activity } from "../../activities/api";
import { formatActivityListRow } from "../../activities/format";
import { useAuth } from "../../auth/AuthContext";
import { toDateKey } from "../../shared/dates";

export function ActivityList() {
  const { user } = useAuth();
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listActivities().then((result) => {
      if (!result.success || !result.activities) {
        setError(result.error ?? "Failed to load activities");
      } else {
        setActivities(result.activities);
      }
      setLoading(false);
    });
  }, []);

  const sorted = useMemo(
    () =>
      [...activities].sort((a, b) => toDateKey(b.date).localeCompare(toDateKey(a.date))),
    [activities],
  );

  if (loading) return <p className="muted">Loading activities…</p>;
  if (error) return <p className="error">{error}</p>;

  return (
    <div className="stack">
      <h2>Activities</h2>
      {sorted.length === 0 ? (
        <p className="muted">
          No activities yet.
          {!user?.strava_connected && " Connect Strava in Settings to import your runs."}
        </p>
      ) : (
        sorted.map((activity) => (
          <Link
            key={activity.id}
            to={`/activity/${activity.id}`}
            className="activity-row card stack"
            style={{ textDecoration: "none", color: "inherit" }}
          >
            <div className="row-between">
              <strong>{activity.name}</strong>
              <span className={`badge ${activity.source === "strava" ? "badge-ok" : "badge-muted"}`}>
                {activity.source}
              </span>
            </div>
            <p className="muted">{formatActivityListRow(activity)}</p>
          </Link>
        ))
      )}
    </div>
  );
}
