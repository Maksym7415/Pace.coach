import { apiDelete, apiGet, apiPost, apiPut } from "../shared/api";
import type { ActivitySummary } from "../activities/api";
import type { WorkoutStepItem } from "../workout/types";

export type WorkoutType =
  | "easy"
  | "recovery"
  | "long_run"
  | "threshold"
  | "intervals"
  | "hills"
  | "race_pace"
  | "rest";

export type WorkoutStatus = "scheduled" | "completed" | "skipped";

export const WORKOUT_TYPES: { value: WorkoutType; label: string }[] = [
  { value: "easy", label: "Easy" },
  { value: "recovery", label: "Recovery" },
  { value: "long_run", label: "Long run" },
  { value: "threshold", label: "Threshold" },
  { value: "intervals", label: "Intervals" },
  { value: "hills", label: "Hills" },
  { value: "race_pace", label: "Race pace" },
  { value: "rest", label: "Rest" },
];

export type WorkoutWriteInput = {
  scheduled_date: string;
  sport_id: number;
  workout_type?: WorkoutType;
  title: string;
  description?: string | null;
  steps: WorkoutStepItem[];
};

export type WorkoutCreateInput = WorkoutWriteInput & {
  athlete_id: number;
};

export type WorkoutUpdateInput = WorkoutWriteInput;

export type Workout = {
  id: number;
  athlete_id: number;
  created_by_id: number | null;
  scheduled_date: string;
  sport_id: number | null;
  sport_code: string | null;
  sport_name: string | null;
  workout_type: WorkoutType;
  title: string;
  description: string | null;
  steps: WorkoutStepItem[] | null;
  duration_min: number | null;
  distance_m: number | null;
  status: WorkoutStatus;
  completed_at: string | null;
  notes: string | null;
  activity_id: number | null;
  linked_activity: ActivitySummary | null;
  created_at: string | null;
  updated_at: string | null;
};

export async function getCalendar(startDate: string, endDate: string) {
  const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
  return apiGet<{ workouts: Workout[]; count: number }>(`/api/training/calendar?${params}`);
}

export async function getAthleteCalendar(athleteId: number, startDate: string, endDate: string) {
  const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
  return apiGet<{ workouts: Workout[]; count: number }>(
    `/api/training/athletes/${athleteId}/calendar?${params}`,
  );
}

export async function createWorkout(input: WorkoutCreateInput) {
  return apiPost<{ workout: Workout }>("/api/training/workouts", input);
}

export async function updateWorkout(workoutId: number, input: WorkoutUpdateInput) {
  return apiPut<{ workout: Workout }>(`/api/training/workouts/${workoutId}`, input);
}

export async function deleteWorkout(workoutId: number) {
  return apiDelete<{ deleted: boolean; workout_id: number }>(
    `/api/training/workouts/${workoutId}`,
  );
}

export async function getWorkout(workoutId: number) {
  return apiGet<{ workout: Workout }>(`/api/training/workouts/${workoutId}`);
}

export async function completeWorkout(workoutId: number, notes?: string) {
  return apiPut<{ workout: Workout }>(`/api/training/workouts/${workoutId}/complete`, { notes });
}

export async function skipWorkout(workoutId: number) {
  return apiPut<{ workout: Workout }>(`/api/training/workouts/${workoutId}/skip`);
}
