import { secsToMMSS } from "../athlete-profile/api";
import type { DurationType, RepeatBlock, TargetType, WorkoutStep, WorkoutStepItem } from "./types";
import { isRepeatBlock, stepTypeLabel } from "./types";

export function formatPaceSeconds(secs: number | null): string {
  if (secs == null) return "—";
  return `${secsToMMSS(Math.round(secs))}/km`;
}

function formatDurationMinutes(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  if (hours > 0) {
    return `${hours}:${mins.toString().padStart(2, "0")}`;
  }
  return `${minutes} min`;
}

function formatDistanceMeters(meters: number): string {
  if (meters >= 1000) return `${(meters / 1000).toFixed(1)} km`;
  return `${meters} m`;
}

function formatStepDuration(step: WorkoutStep): string | null {
  const durationType: DurationType =
    step.durationType ??
    (step.distance != null && step.duration == null
      ? "distance"
      : step.duration != null
        ? "time"
        : "lap_button");

  if (durationType === "lap_button") return "Lap button";
  if (durationType === "time" && step.duration != null) {
    return formatDurationMinutes(step.duration);
  }
  if (durationType === "distance" && step.distance != null) {
    return formatDistanceMeters(step.distance);
  }
  return null;
}

export function formatTarget(
  targetType: TargetType | null,
  targetMin: number | null,
  targetMax: number | null,
  targetZoneName: string | null,
  sportCode?: string | null,
): string | null {
  if (!targetType || targetType === "none") return null;

  if (targetZoneName && targetMin != null && targetMax != null) {
    if (targetType === "heart_rate") {
      return `${targetZoneName} (${targetMin}–${targetMax} bpm)`;
    }
    if (targetType === "power") {
      return `${targetZoneName} (${targetMin}–${targetMax} W)`;
    }
  }

  if (targetMin == null && targetMax == null) return null;

  let range: string;
  if (targetType === "pace") {
    const min = targetMin != null ? formatPaceSeconds(targetMin) : "—";
    const max = targetMax != null ? formatPaceSeconds(targetMax) : "—";
    range = `${min} – ${max}`;
  } else if (targetType === "heart_rate") {
    range = `${targetMin ?? "—"}–${targetMax ?? "—"} bpm`;
  } else if (targetType === "power") {
    range = `${targetMin ?? "—"}–${targetMax ?? "—"} W`;
  } else if (targetType === "cadence") {
    const unit = sportCode === "cycling" ? "rpm" : "spm";
    range = `${targetMin ?? "—"}–${targetMax ?? "—"} ${unit}`;
  } else {
    return null;
  }

  if (targetZoneName) {
    return `${targetZoneName} · ${range}`;
  }
  return range;
}

export function formatStepSummary(step: WorkoutStep, sportCode?: string | null): string {
  const parts: string[] = [stepTypeLabel(step.type)];
  const durationLabel = formatStepDuration(step);
  if (durationLabel) parts.push(durationLabel);
  const target = formatTarget(
    step.targetType,
    step.targetMin,
    step.targetMax,
    step.targetZoneName,
    sportCode,
  );
  if (target) parts.push(target);
  if (step.notes) parts.push(step.notes);
  return parts.join(" · ");
}

export function formatRepeatBlockSummary(block: RepeatBlock, sportCode?: string | null): string {
  const inner = block.steps.map((s) => formatStepSummary(s, sportCode)).join("; ");
  return `${block.repeatCount}× (${inner})`;
}

export function formatWorkoutPreview(
  steps: WorkoutStepItem[] | null | undefined,
  sportCode?: string | null,
  compact = false,
): string[] {
  if (!steps || !Array.isArray(steps) || steps.length === 0) return [];

  if (compact) {
    const first = steps[0];
    const line = isRepeatBlock(first)
      ? formatRepeatBlockSummary(first, sportCode)
      : formatStepSummary(first, sportCode);
    const extra = steps.length > 1 ? ` (+${steps.length - 1} more)` : "";
    return [`${line}${extra}`];
  }

  const lines: string[] = [];
  for (const item of steps) {
    if (isRepeatBlock(item)) {
      lines.push(`Repeat ${item.repeatCount}×:`);
      for (const step of item.steps) {
        lines.push(`  ${formatStepSummary(step, sportCode)}`);
      }
    } else {
      lines.push(formatStepSummary(item, sportCode));
    }
  }
  return lines;
}
