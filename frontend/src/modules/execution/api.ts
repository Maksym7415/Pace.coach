import { apiGet } from "../shared/api";
import type { WorkoutExecution } from "./types";

export async function getWorkoutExecution(activityId: number) {
  return apiGet<{ workout_execution: WorkoutExecution | null }>(
    `/api/activities/${activityId}/workout-execution`,
  );
}
