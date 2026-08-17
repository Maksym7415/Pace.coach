import { apiGet, apiPost } from "../shared/api";
import type { WorkoutExecution } from "./types";

export async function getWorkoutExecution(activityId: number) {
  return apiGet<{ workout_execution: WorkoutExecution | null }>(
    `/api/activities/${activityId}/workout-execution`,
  );
}

export async function rematchWorkoutExecution(activityId: number) {
  return apiPost<{ workout_execution: WorkoutExecution }>(
    `/api/activities/${activityId}/workout-execution/rematch`,
    {},
  );
}

export type AthleteIssueResponsePayload = {
  issue_id: number;
  reason?: string | null;
  reason_other?: string | null;
  notes?: string | null;
};

export async function saveAthleteResponses(
  activityId: number,
  responses: AthleteIssueResponsePayload[],
) {
  return apiPost<{ updated: number; workout_execution: WorkoutExecution }>(
    `/api/activities/${activityId}/workout-execution/athlete-responses`,
    { responses },
  );
}
