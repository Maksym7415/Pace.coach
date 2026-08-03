import type { Activity } from "./api";
import { formatDate, toDateKey } from "../shared/dates";

export function formatDistance(km: number | null | undefined): string {
  if (km === null || km === undefined) return "—";
  return `${km.toFixed(1)} km`;
}

export function formatDuration(hours: number | null | undefined): string {
  if (hours === null || hours === undefined) return "—";
  return `${hours.toFixed(1)} h`;
}

/** Compact duration for list rows, e.g. `1h 32m` or `45m`. */
export function formatDurationCompact(hours: number | null | undefined): string | null {
  if (hours === null || hours === undefined) return null;
  const totalMinutes = Math.round(hours * 60);
  const h = Math.floor(totalMinutes / 60);
  const m = totalMinutes % 60;
  if (h <= 0) return `${m}m`;
  if (m === 0) return `${h}h`;
  return `${h}h ${m}m`;
}

type ActivityLike = {
  total_distance_km: number | null;
  total_hours: number | null;
  sport_code: string | null;
  activity_type_code: string | null;
};

function activityTypeLabel(activity: ActivityLike): string {
  return activity.activity_type_code ?? activity.sport_code ?? "unknown";
}

export function formatActivityMeta(activity: ActivityLike): string {
  return [
    formatDistance(activity.total_distance_km),
    formatDuration(activity.total_hours),
    activityTypeLabel(activity),
  ].join(" · ");
}

export function formatActivityListRow(activity: Activity): string {
  return [
    formatDate(activity.date),
    formatDistance(activity.total_distance_km),
    formatDuration(activity.total_hours),
    activityTypeLabel(activity),
  ].join(" · ");
}

/** List meta like `Wed · 1h 32m · 11.4 km`. */
export function formatActivityListMeta(activity: Activity): string {
  const [y, m, d] = toDateKey(activity.date).split("-").map(Number);
  const weekday = new Date(y, m - 1, d).toLocaleDateString(undefined, { weekday: "short" });
  const parts = [weekday];
  const duration = formatDurationCompact(activity.total_hours);
  if (duration) parts.push(duration);
  if (activity.total_distance_km != null) parts.push(formatDistance(activity.total_distance_km));
  return parts.join(" · ");
}
