import type { WorkoutStatus } from "../training/api";
import { toDateKey } from "../shared/dates";

export type CalendarDisplayStatus = "completed" | "planned" | "missed";

export const STATUS_LEGEND: {
  id: CalendarDisplayStatus;
  label: string;
  dotClass: string;
}[] = [
  { id: "completed", label: "Completed activity", dotClass: "calendar-status-dot-completed" },
  { id: "planned", label: "Planned workout", dotClass: "calendar-status-dot-planned" },
  { id: "missed", label: "Not executed", dotClass: "calendar-status-dot-missed" },
];

export const STATUS_BADGE_LABEL: Record<CalendarDisplayStatus, string> = {
  completed: "Completed",
  planned: "Planned",
  missed: "Not executed",
};

export function displayStatusForActivity(): CalendarDisplayStatus {
  return "completed";
}

export function displayStatusForWorkout(
  workout: { status: WorkoutStatus; scheduled_date: string },
  today: string,
): CalendarDisplayStatus {
  if (workout.status === "completed") return "completed";
  if (workout.status === "skipped") return "missed";
  const date = toDateKey(workout.scheduled_date);
  if (date < toDateKey(today)) return "missed";
  return "planned";
}

export function chipClassForStatus(status: CalendarDisplayStatus): string {
  return `calendar-status-chip calendar-status-chip-${status}`;
}
