import type { DurationType, WorkoutStep, WorkoutStepItem } from "./types";
import { isRepeatBlock } from "./types";

function inferDurationType(step: WorkoutStep): DurationType {
  if (step.durationType) return step.durationType;
  if (step.distance != null && step.duration == null) return "distance";
  if (step.duration != null && step.distance == null) return "time";
  if (step.duration != null && step.distance != null) {
    return step.type === "interval" ? "distance" : "time";
  }
  return "lap_button";
}

export function normalizeWorkoutStep(step: WorkoutStep): WorkoutStep {
  const durationType = inferDurationType(step);
  const normalized: WorkoutStep = { ...step, durationType };

  if (durationType === "time") {
    normalized.distance = null;
  } else if (durationType === "distance") {
    normalized.duration = null;
  } else {
    normalized.duration = null;
    normalized.distance = null;
  }

  return normalized;
}

export function normalizeWorkoutSteps(steps: WorkoutStepItem[]): WorkoutStepItem[] {
  return steps.map((item) => {
    if (isRepeatBlock(item)) {
      return {
        ...item,
        steps: item.steps.map(normalizeWorkoutStep),
      };
    }
    return normalizeWorkoutStep(item);
  });
}

export function validateWorkoutStepDuration(step: WorkoutStep): string | null {
  const durationType = step.durationType ?? inferDurationType(step);
  if (durationType === "time" && step.duration == null) {
    return "Each time-based step needs a duration";
  }
  if (durationType === "distance" && step.distance == null) {
    return "Each distance-based step needs a distance";
  }
  return null;
}
