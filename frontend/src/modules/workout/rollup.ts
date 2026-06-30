import type { WorkoutStep, WorkoutStepItem } from "./types";
import { isRepeatBlock } from "./types";

function rollupLeaf(step: WorkoutStep): { duration: number; distance: number } {
  const durationType = step.durationType ?? (step.distance != null ? "distance" : "time");
  if (durationType === "lap_button") {
    return { duration: 0, distance: 0 };
  }
  return {
    duration: step.duration ?? 0,
    distance: step.distance ?? 0,
  };
}

export function computeRollups(steps: WorkoutStepItem[]): {
  durationMin: number | null;
  distanceM: number | null;
} {
  let totalDuration = 0;
  let totalDistance = 0;
  let hasDuration = false;
  let hasDistance = false;

  for (const item of steps) {
    if (isRepeatBlock(item)) {
      let blockDuration = 0;
      let blockDistance = 0;
      let blockHasDuration = false;
      let blockHasDistance = false;
      for (const step of item.steps) {
        const { duration, distance } = rollupLeaf(step);
        if (duration) {
          blockHasDuration = true;
          blockDuration += duration;
        }
        if (distance) {
          blockHasDistance = true;
          blockDistance += distance;
        }
      }
      if (blockHasDuration) {
        hasDuration = true;
        totalDuration += blockDuration * item.repeatCount;
      }
      if (blockHasDistance) {
        hasDistance = true;
        totalDistance += blockDistance * item.repeatCount;
      }
    } else {
      const { duration, distance } = rollupLeaf(item);
      if (duration) {
        hasDuration = true;
        totalDuration += duration;
      }
      if (distance) {
        hasDistance = true;
        totalDistance += distance;
      }
    }
  }

  return {
    durationMin: hasDuration ? totalDuration : null,
    distanceM: hasDistance ? totalDistance : null,
  };
}
