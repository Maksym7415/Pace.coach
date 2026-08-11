import { Link } from "react-router-dom";
import type { Activity } from "../../activities/api";
import { formatActivityListMeta } from "../../activities/format";
import {
  activityMatchesSportFilter,
  toSportFilterId,
  type SportFilterId,
} from "../../activities/sportFilter";
import type { ActivityListRangeId } from "../../shared/dates";
import { toDateKey } from "../../shared/dates";
import { useAuth } from "../../auth/AuthContext";
import { cn } from "@/lib/utils";

const RANGES: { id: ActivityListRangeId; label: string }[] = [
  { id: "7d", label: "Last 7 days" },
  { id: "30d", label: "Last 30 days" },
  { id: "week", label: "This week" },
  { id: "month", label: "This month" },
  { id: "year", label: "This year" },
];

export type ActivityListProps = {
  activities: Activity[];
  sportFilter: SportFilterId[];
  rangeId: ActivityListRangeId;
  onRangeChange: (id: ActivityListRangeId) => void;
  loading?: boolean;
  error?: string | null;
  /** Hide athlete-only empty hints (Strava connect). */
  coachMode?: boolean;
};

export function ActivityList({
  activities,
  sportFilter,
  rangeId,
  onRangeChange,
  loading = false,
  error = null,
  coachMode = false,
}: ActivityListProps) {
  const { user } = useAuth();

  const visible = [...activities]
    .filter((a) => activityMatchesSportFilter(a, sportFilter))
    .sort((a, b) => toDateKey(b.date).localeCompare(toDateKey(a.date)));

  return (
    <div className="stack">
      <div className="flex flex-wrap gap-2">
        {RANGES.map((r) => (
          <button
            key={r.id}
            type="button"
            className={cn(
              "activities-chip activities-chip-filter",
              rangeId === r.id && "activities-chip-active",
            )}
            onClick={() => onRangeChange(r.id)}
            aria-pressed={rangeId === r.id}
          >
            {r.label}
          </button>
        ))}
      </div>

      {loading && <p className="muted">Loading activities…</p>}
      {error && <p className="error">{error}</p>}

      {!loading && !error && activities.length === 0 && (
        <p className="muted">
          No activities in this range.
          {!coachMode && !user?.strava_connected
            ? " Connect Strava in Settings to import your runs."
            : ""}
        </p>
      )}

      {!loading && !error && activities.length > 0 && visible.length === 0 && (
        <p className="muted">No activities for the selected sports.</p>
      )}

      {!loading && !error && visible.length > 0 && (
        <ul className="stack" style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {visible.map((activity) => (
            <li key={activity.id}>
              <Link
                to={`/activity/${activity.id}`}
                className="activity-row card stack"
                style={{ textDecoration: "none", color: "inherit", display: "block" }}
              >
                <div className="row-between">
                  <div>
                    <span className="muted" style={{ fontSize: "11px", textTransform: "uppercase" }}>
                      {toSportFilterId(activity.sport_code)}
                    </span>
                    <div>
                      <strong>{activity.name}</strong>
                    </div>
                    <p className="muted">{formatActivityListMeta(activity)}</p>
                  </div>
                  <span className="muted" style={{ fontSize: "12px" }}>
                    Open →
                  </span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
