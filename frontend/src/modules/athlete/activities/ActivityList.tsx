import { useEffect, useMemo, useState } from "react";
import { getActivity, listActivities, type Activity } from "../../activities/api";
import { formatActivityListRow } from "../../activities/format";
import { useAuth } from "../../auth/AuthContext";
import { toDateKey } from "../../shared/dates";

function ActivityRow({
  activity,
  expanded,
  onToggle,
}: {
  activity: Activity;
  expanded: boolean;
  onToggle: () => void;
}) {
  const [detail, setDetail] = useState<Activity | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!expanded) {
      setDetail(null);
      return;
    }
    setLoading(true);
    getActivity(activity.id).then((result) => {
      if (result.success && result.activity) setDetail(result.activity);
      setLoading(false);
    });
  }, [expanded, activity.id]);

  return (
    <div className="activity-row card stack">
      <button type="button" className="activity-row-header" onClick={onToggle}>
        <div className="row-between">
          <strong>{activity.name}</strong>
          <span className={`badge ${activity.source === "strava" ? "badge-ok" : "badge-muted"}`}>
            {activity.source}
          </span>
        </div>
        <p className="muted">{formatActivityListRow(activity)}</p>
      </button>
      {expanded && (
        <div className="activity-detail">
          {loading && <p className="muted">Loading details…</p>}
          {detail && (
            <dl className="detail-list">
              <div>
                <dt>Sessions</dt>
                <dd>{detail.total_sessions ?? "—"}</dd>
              </div>
              {detail.strava_activity_id && (
                <div>
                  <dt>Strava ID</dt>
                  <dd>{detail.strava_activity_id}</dd>
                </div>
              )}
            </dl>
          )}
        </div>
      )}
    </div>
  );
}

export function ActivityList() {
  const { user } = useAuth();
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);

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
          <ActivityRow
            key={activity.id}
            activity={activity}
            expanded={expandedId === activity.id}
            onToggle={() => setExpandedId((id) => (id === activity.id ? null : activity.id))}
          />
        ))
      )}
    </div>
  );
}
