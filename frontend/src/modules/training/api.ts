import { apiGet, apiPut } from "../shared/api";

import type { ActivitySummary } from "../activities/api";

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

export type Workout = {
  id: number;
  athlete_id: number;
  created_by_id: number | null;
  scheduled_date: string;
  workout_type: WorkoutType;
  title: string;
  description: string | null;
  steps: unknown;
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

export async function getWorkout(workoutId: number) {
  return apiGet<{ workout: Workout }>(`/api/training/workouts/${workoutId}`);
}

export async function completeWorkout(workoutId: number, notes?: string) {
  return apiPut<{ workout: Workout }>(`/api/training/workouts/${workoutId}/complete`, { notes });
}

export async function skipWorkout(workoutId: number) {
  return apiPut<{ workout: Workout }>(`/api/training/workouts/${workoutId}/skip`);
}
