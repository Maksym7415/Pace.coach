import { apiGet } from "../shared/api";

export type Activity = {
  id: number;
  name: string;
  date: string;
  total_distance_km: number | null;
  total_hours: number | null;
  total_sessions: number | null;
  activity_type: string | null;
  source: string;
  strava_activity_id: number | null;
  created_at: string | null;
};

export type ActivitySummary = Pick<
  Activity,
  "id" | "name" | "date" | "total_distance_km" | "total_hours" | "activity_type" | "source"
>;

export async function listActivities(startDate?: string, endDate?: string) {
  const params = new URLSearchParams();
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  const query = params.toString();
  return apiGet<{ activities: Activity[] }>(`/api/activities${query ? `?${query}` : ""}`);
}

export async function getActivity(activityId: number) {
  return apiGet<{ activity: Activity }>(`/api/activities/${activityId}`);
}
