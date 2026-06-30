import { apiGet, apiPost, apiPut } from "../shared/api";

export type CoachAthleteSummary = {
  id: number;
  name: string;
  username: string;
  email: string;
};

export type CoachAthleteListItem = {
  relation_id: number;
  athlete: CoachAthleteSummary;
  status: string;
  created_at: string | null;
};

export type CoachAthleteDetail = {
  relation_id: number;
  coaching_since: string | null;
  athlete: CoachAthleteSummary;
  upcoming_workouts_count: number;
};

export type SearchUser = {
  id: number;
  name: string;
  username: string;
  roles: string[];
};

export async function listAthletes() {
  return apiGet<{ athletes: CoachAthleteListItem[]; count: number }>("/api/coaching/athletes");
}

export async function getAthlete(athleteId: number) {
  return apiGet<CoachAthleteDetail>(`/api/coaching/athletes/${athleteId}`);
}

export async function searchUsers(query: string, role: "athlete" | "coach" = "athlete") {
  const params = new URLSearchParams({ q: query, role });
  return apiGet<{ users: SearchUser[] }>(`/api/coaching/users/search?${params}`);
}

export async function inviteAthlete(athleteId: number) {
  return apiPost<{ relation: { id: number; status: string } }>("/api/coaching/invitations", {
    athlete_id: athleteId,
  });
}

export type PendingInvitation = {
  relation_id: number;
  coach: CoachAthleteSummary;
  status: string;
  created_at: string | null;
};

export async function listPendingInvitations() {
  return apiGet<{ invitations: PendingInvitation[]; count: number }>(
    "/api/coaching/invitations/pending",
  );
}

export async function acceptInvitation(relationId: number) {
  return apiPut<{ relation: { id: number; status: string } }>(
    `/api/coaching/invitations/${relationId}/accept`,
  );
}

export async function rejectInvitation(relationId: number) {
  return apiPut<{ relation: { id: number; status: string } }>(
    `/api/coaching/invitations/${relationId}/reject`,
  );
}
