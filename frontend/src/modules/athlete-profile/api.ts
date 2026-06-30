import { apiDelete, apiGet, apiPost, apiPut } from "../shared/api";

export type Sport = {
  id: number;
  code: string;
  name: string;
};

export type AthleteSport = {
  id: number;
  sport: Sport;
  is_primary: boolean;
  created_at: string | null;
};

export type Baseline = {
  id: number;
  athlete_id: number;
  hrv_baseline_min: number | null;
  hrv_baseline_max: number | null;
  resting_hr_baseline: number | null;
  created_at: string | null;
  updated_at: string | null;
};

export type BodyMetric = {
  id: number;
  athlete_id: number;
  weight_kg: number | null;
  height_cm: number | null;
  measured_at: string;
  created_at: string | null;
};

export type ZoneSource =
  | "manual"
  | "garmin"
  | "strava"
  | "ftp_calculation"
  | "threshold_pace_calculation"
  | "threshold_hr_calculation";

export type ZoneCategory = "hr" | "pace" | "power";

export type SportProfile = {
  id: number;
  athlete_id: number;
  sport: Sport;
  threshold_pace_sec_per_km: number | null;
  threshold_hr: number | null;
  ftp_watts: number | null;
  css_pace_sec_per_100m: number | null;
  zone_source: ZoneSource | null;
  created_at: string | null;
  updated_at: string | null;
};

export type Zone = {
  id: number;
  athlete_sport_profile_id: number;
  zone_category: ZoneCategory;
  zone_name: string;
  min_value: number;
  max_value: number;
  created_at: string | null;
};

export const ZONE_SOURCES: { value: ZoneSource; label: string }[] = [
  { value: "manual", label: "Manual" },
  { value: "garmin", label: "Garmin" },
  { value: "strava", label: "Strava" },
  { value: "ftp_calculation", label: "FTP calculation" },
  { value: "threshold_pace_calculation", label: "Threshold pace calculation" },
  { value: "threshold_hr_calculation", label: "Threshold HR calculation" },
];

export const ZONE_CATEGORIES: { value: ZoneCategory; label: string }[] = [
  { value: "hr", label: "Heart rate" },
  { value: "pace", label: "Pace" },
  { value: "power", label: "Power" },
];

export function secsToMMSS(secs: number): string {
  const minutes = Math.floor(secs / 60);
  const seconds = secs % 60;
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

export function mmssToSecs(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parts = trimmed.split(":");
  if (parts.length !== 2) return null;
  const minutes = Number.parseInt(parts[0], 10);
  const seconds = Number.parseInt(parts[1], 10);
  if (Number.isNaN(minutes) || Number.isNaN(seconds) || seconds >= 60 || minutes < 0) {
    return null;
  }
  return minutes * 60 + seconds;
}

export function formatPaceValue(secs: number | null, unit: string): string {
  if (secs == null) return "—";
  return `${secsToMMSS(secs)} / ${unit}`;
}

// Athlete-facing API

export async function listSports() {
  return apiGet<{ sports: Sport[]; count: number }>("/api/athlete-profile/sports");
}

export async function listMySports() {
  return apiGet<{ sports: AthleteSport[]; count: number }>("/api/athlete-profile/my/sports");
}

export async function addMySport(sportId: number, isPrimary = false) {
  return apiPost<{ sport: AthleteSport }>("/api/athlete-profile/my/sports", {
    sport_id: sportId,
    is_primary: isPrimary,
  });
}

export async function removeMySport(sportId: number) {
  return apiDelete<{ removed: boolean }>(`/api/athlete-profile/my/sports/${sportId}`);
}

export async function setMyPrimarySport(sportId: number) {
  return apiPut<{ sport: AthleteSport }>(`/api/athlete-profile/my/sports/${sportId}/primary`);
}

export async function getMyBaselines() {
  return apiGet<{ baseline: Baseline }>("/api/athlete-profile/my/baselines");
}

export async function upsertMyBaselines(data: {
  hrv_baseline_min?: number | null;
  hrv_baseline_max?: number | null;
  resting_hr_baseline?: number | null;
}) {
  return apiPut<{ baseline: Baseline }>("/api/athlete-profile/my/baselines", data);
}

export async function addMyBodyMetric(data: {
  weight_kg?: number | null;
  height_cm?: number | null;
  measured_at: string;
}) {
  return apiPost<{ metric: BodyMetric }>("/api/athlete-profile/my/body-metrics", data);
}

export async function listMyBodyMetrics(limit = 20) {
  return apiGet<{ metrics: BodyMetric[]; count: number }>(
    `/api/athlete-profile/my/body-metrics?limit=${limit}`,
  );
}

export async function getMySportProfile(sportId: number) {
  return apiGet<{ profile: SportProfile }>(`/api/athlete-profile/my/sport-profiles/${sportId}`);
}

export async function upsertMySportProfile(
  sportId: number,
  data: {
    threshold_pace_sec_per_km?: number | null;
    threshold_hr?: number | null;
    ftp_watts?: number | null;
    css_pace_sec_per_100m?: number | null;
    zone_source?: ZoneSource | null;
  },
) {
  return apiPut<{ profile: SportProfile }>(
    `/api/athlete-profile/my/sport-profiles/${sportId}`,
    data,
  );
}

async function listZones(path: string) {
  const response = await fetch(`${API_BASE}${path}`, { headers: authHeaders() });
  if (response.status === 404) {
    return { success: true as const, zones: [] as Zone[], count: 0 };
  }
  return response.json() as Promise<ApiEnvelope<{ zones: Zone[]; count: number }>>;
}

export async function listMyZones(sportId: number) {
  return listZones(`/api/athlete-profile/my/sport-profiles/${sportId}/zones`);
}

export async function createMyZone(
  sportId: number,
  data: {
    zone_category: ZoneCategory;
    zone_name: string;
    min_value: number;
    max_value: number;
  },
) {
  return apiPost<{ zone: Zone }>(`/api/athlete-profile/my/sport-profiles/${sportId}/zones`, data);
}

export async function deleteMyZone(zoneId: number) {
  return apiDelete<{ removed: boolean }>(`/api/athlete-profile/my/zones/${zoneId}`);
}

// Coach-facing API

export async function listAthleteSports(athleteId: number) {
  return apiGet<{ sports: AthleteSport[]; count: number }>(
    `/api/athlete-profile/athletes/${athleteId}/sports`,
  );
}

export async function getAthleteBaselines(athleteId: number) {
  return apiGet<{ baseline: Baseline }>(`/api/athlete-profile/athletes/${athleteId}/baselines`);
}

export async function getAthleteSportProfile(athleteId: number, sportId: number) {
  return apiGet<{ profile: SportProfile }>(
    `/api/athlete-profile/athletes/${athleteId}/sport-profiles/${sportId}`,
  );
}

export async function listAthleteZones(athleteId: number, sportId: number) {
  return listZones(
    `/api/athlete-profile/athletes/${athleteId}/sport-profiles/${sportId}/zones`,
  );
}
