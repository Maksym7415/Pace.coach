import { Link } from "react-router-dom";
import type { Activity } from "../../activities/api";
import { formatActivityMeta } from "../../activities/format";

type ActivityCardProps = {
  activity: Activity;
  compact?: boolean;
};

export function ActivityCard({ activity, compact = false }: ActivityCardProps) {
  return (
    <Link
      to={`/activity/${activity.id}`}
      className={`activity-card ${compact ? "activity-card-compact" : ""}`}
      style={{ textDecoration: "none", color: "inherit", display: "block" }}
    >
      <div className="row-between">
        <strong>{activity.name}</strong>
        <span className={`badge ${activity.source === "strava" ? "badge-ok" : "badge-muted"}`}>
          {activity.source}
        </span>
      </div>
      <p className="muted">{formatActivityMeta(activity)}</p>
    </Link>
  );
}
