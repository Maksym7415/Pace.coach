import { apiFetch, apiGet, apiPost } from "../shared/api";

export type RecoveryEntry = {
  id: number;
  user_id: number;
  entry_date: string;
  hrv_ms: number | null;
  resting_hr_bpm: number | null;
  body_battery: number | null;
  fatigue: number | null;
  soreness: number | null;
  mood: number | null;
  sleep_quality: number | null;
  sleep_hours: number | null;
  readiness_score: number | null;
  notes: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type RecoveryEntryInput = {
  entry_date: string;
  hrv_ms?: number | null;
  resting_hr_bpm?: number | null;
  body_battery?: number | null;
  fatigue?: number | null;
  soreness?: number | null;
  mood?: number | null;
  sleep_quality?: number | null;
  sleep_hours?: number | null;
  notes?: string | null;
};

export async function getTodayEntry(): Promise<{ entry: RecoveryEntry | null; error?: string }> {
  const response = await apiFetch("/api/recovery/entries/today");
  if (response.status === 404) return { entry: null };
  const result = await response.json();
  if (!result.success || !result.entry) {
    return { entry: null, error: result.error };
  }
  return { entry: result.entry };
}

export async function upsertEntry(data: RecoveryEntryInput) {
  return apiPost<{ entry: RecoveryEntry }>("/api/recovery/entries", data);
}

export async function listEntries(startDate: string, endDate: string) {
  const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
  return apiGet<{ entries: RecoveryEntry[]; count: number }>(`/api/recovery/entries?${params}`);
}

export async function getAthleteTodayEntry(athleteId: number) {
  return apiGet<{ entry: RecoveryEntry | null }>(
    `/api/recovery/athletes/${athleteId}/entries/today`,
  );
}
