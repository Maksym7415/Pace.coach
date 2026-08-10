import { formatDistance, formatDurationCompact } from "../activities/format";
import { formatStepSummary, formatTarget } from "../workout/format";
import type { DurationType, StepType, TargetType, WorkoutStep } from "../workout/types";
import type { PlannedStep, StepExecution } from "./types";

function plannedToWorkoutStep(planned: PlannedStep): WorkoutStep {
  return {
    type: planned.step_type as StepType,
    durationType: (planned.duration_type as DurationType | null) ?? undefined,
    duration: planned.duration_min,
    distance: planned.distance_m,
    targetType: (planned.target_type as TargetType | null) ?? null,
    targetMin: planned.target_min,
    targetMax: planned.target_max,
    targetZoneId: null,
    targetZoneName: planned.target_zone_name,
    notes: planned.notes,
  };
}

export function formatPlannedLabel(planned: PlannedStep, sportCode?: string | null): string {
  return formatStepSummary(plannedToWorkoutStep(planned), sportCode);
}

function formatActualDuration(seconds: number | null): string | null {
  if (seconds == null) return null;
  return formatDurationCompact(seconds / 3600);
}

function formatActualDistance(meters: number | null): string | null {
  if (meters == null) return null;
  if (meters < 1000) return `${Math.round(meters)} m`;
  return formatDistance(meters / 1000);
}

function formatActualTarget(step: StepExecution): string | null {
  if (step.time_in_target_pct != null) {
    return `${Math.round(step.time_in_target_pct)}% in target`;
  }
  if (step.target_deviation_pct != null) {
    const signed = step.target_deviation_pct > 0 ? "+" : "";
    return `${signed}${Math.round(step.target_deviation_pct)}% vs target`;
  }
  return null;
}

export function formatActualLabel(step: StepExecution, _sportCode?: string | null): string {
  if (step.status === "not_executed" || step.status === "not_attempted") {
    return "—";
  }
  if (step.status === "unmatched") {
    return "No match";
  }

  const parts: string[] = [];
  const duration = formatActualDuration(step.duration_moving_s);
  if (duration) parts.push(duration);
  const distance = formatActualDistance(step.distance_m);
  if (distance) parts.push(distance);
  const target = formatActualTarget(step);
  if (target) parts.push(target);

  if (parts.length === 0) return "Executed";
  return parts.join(" · ");
}

/** Compact expected/actual lines for the review drawer cards. */
export function formatExpectedLines(planned: PlannedStep, sportCode?: string | null): string[] {
  const step = plannedToWorkoutStep(planned);
  const lines: string[] = [];
  if (planned.duration_type === "distance" && planned.distance_m != null) {
    lines.push(
      planned.distance_m < 1000
        ? `${planned.distance_m} m`
        : formatDistance(planned.distance_m / 1000),
    );
  } else if (planned.duration_type === "time" && planned.duration_min != null) {
    lines.push(formatDurationCompact(planned.duration_min / 60) ?? `${planned.duration_min}m`);
  } else if (planned.duration_type === "lap_button") {
    lines.push("Lap button");
  }
  const target = formatTarget(
    step.targetType,
    step.targetMin,
    step.targetMax,
    step.targetZoneName,
    sportCode,
  );
  if (target) lines.push(target);
  if (!lines.length) lines.push(formatPlannedLabel(planned, sportCode));
  return lines;
}

export function formatActualLines(step: StepExecution, sportCode?: string | null): string[] {
  if (step.status === "not_executed" || step.status === "not_attempted") {
    return ["Skipped"];
  }
  if (step.status === "unmatched") {
    return ["No match"];
  }
  const lines: string[] = [];
  const duration = formatActualDuration(step.duration_moving_s);
  if (duration) lines.push(duration);
  const distance = formatActualDistance(step.distance_m);
  if (distance) lines.push(distance);
  const target = formatActualTarget(step);
  if (target) lines.push(target);
  if (!lines.length) lines.push(formatActualLabel(step, sportCode));
  return lines;
}
