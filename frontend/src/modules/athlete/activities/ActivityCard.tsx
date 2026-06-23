import type { Activity } from "../../activities/api";
import { formatActivityMeta } from "../../activities/format";

type ActivityCardProps = {
  activity: Activity;
  compact?: boolean;
};

export function ActivityCard({ activity, compact = false }: ActivityCardProps) {
  return (
    <article className={`activity-card ${compact ? "activity-card-compact" : ""}`}>
      <div className="row-between">
        <strong>{activity.name}</strong>
        <span className={`badge ${activity.source === "strava" ? "badge-ok" : "badge-muted"}`}>
          {activity.source}
        </span>
      </div>
      <p className="muted">{formatActivityMeta(activity)}</p>
    </article>
  );
}
