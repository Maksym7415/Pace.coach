import type { Activity } from "./api";
import { formatDate } from "../shared/dates";

export function formatDistance(km: number | null | undefined): string {
  if (km === null || km === undefined) return "—";
  return `${km.toFixed(1)} km`;
}

export function formatDuration(hours: number | null | undefined): string {
  if (hours === null || hours === undefined) return "—";
  return `${hours.toFixed(1)} h`;
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
