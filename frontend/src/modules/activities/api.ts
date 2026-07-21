import { apiFetch, apiGet, type ApiEnvelope } from "../shared/api";

export type Activity = {
  id: number;
  name: string;
  date: string;
  start_time: string | null;
  total_distance_km: number | null;
  total_hours: number | null;
  total_sessions: number | null;
  sport_id: number | null;
  sport_code: string | null;
  activity_type_id: number | null;
  activity_type_code: string | null;
  source: string;
  strava_activity_id: number | null;
  created_at: string | null;
};

export type ActivitySummary = Pick<
  Activity,
  | "id"
  | "name"
  | "date"
  | "total_distance_km"
  | "total_hours"
  | "sport_id"
  | "sport_code"
  | "activity_type_id"
  | "activity_type_code"
  | "source"
>;

export type FitImportResult = {
  jobId: string;
  status: string;
};

export async function listActivities(startDate?: string, endDate?: string) {
  const params = new URLSearchParams();
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  const query = params.toString();
  return apiGet<{ activities: Activity[] }>(`/api/activities${query ? `?${query}` : ""}`);
}

export async function listAthleteActivities(
  athleteId: number,
  startDate?: string,
  endDate?: string,
) {
  const params = new URLSearchParams();
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  const query = params.toString();
  return apiGet<{ activities: Activity[] }>(
    `/api/activities/athletes/${athleteId}${query ? `?${query}` : ""}`,
  );
}

export async function getActivity(activityId: number) {
  return apiGet<{ activity: Activity }>(`/api/activities/${activityId}`);
}

export async function importFitFile(
  athleteId: number,
  file: File,
): Promise<ApiEnvelope<FitImportResult>> {
  const formData = new FormData();
  formData.append("athlete_id", String(athleteId));
  formData.append("file", file);

  const response = await apiFetch("/api/activities/import/fit", {
    method: "POST",
    body: formData,
  });
  return response.json();
}
