import type { WorkoutType } from "../training/api";

export type StepType =
  | "warmup"
  | "run"
  | "interval"
  | "recovery"
  | "cooldown"
  | "rest"
  | "ride"
  | "recovery_ride";

export type TargetType = "none" | "heart_rate" | "pace" | "power" | "cadence";

export type DurationType = "time" | "distance" | "lap_button";

export type WorkoutStep = {
  type: StepType;
  durationType?: DurationType;
  duration: number | null;
  distance: number | null;
  targetType: TargetType | null;
  targetMin: number | null;
  targetMax: number | null;
  targetZoneId: number | null;
  targetZoneName: string | null;
  notes: string | null;
};

export type RepeatBlock = {
  repeatCount: number;
  steps: WorkoutStep[];
};

export type WorkoutStepItem = WorkoutStep | RepeatBlock;

export function isRepeatBlock(item: WorkoutStepItem): item is RepeatBlock {
  return "repeatCount" in item;
}

export const RUNNING_STEP_TYPES: { value: StepType; label: string }[] = [
  { value: "warmup", label: "Warmup" },
  { value: "run", label: "Run" },
  { value: "interval", label: "Interval" },
  { value: "recovery", label: "Recovery" },
  { value: "cooldown", label: "Cooldown" },
  { value: "rest", label: "Rest" },
];

export const CYCLING_STEP_TYPES: { value: StepType; label: string }[] = [
  { value: "warmup", label: "Warmup" },
  { value: "ride", label: "Ride" },
  { value: "interval", label: "Interval" },
  { value: "recovery", label: "Recovery" },
  { value: "recovery_ride", label: "Recovery ride" },
  { value: "cooldown", label: "Cooldown" },
  { value: "rest", label: "Rest" },
];

export const BUILDER_SPORT_CODES = new Set(["running", "cycling"]);

export const TARGET_TYPES: { value: TargetType; label: string }[] = [
  { value: "none", label: "None" },
  { value: "heart_rate", label: "Heart rate" },
  { value: "pace", label: "Pace" },
  { value: "power", label: "Power" },
  { value: "cadence", label: "Cadence" },
];

export function stepTypesForSport(sportCode: string | null | undefined) {
  if (sportCode === "cycling") return CYCLING_STEP_TYPES;
  return RUNNING_STEP_TYPES;
}

export function stepTypeLabel(type: StepType): string {
  const all = [...RUNNING_STEP_TYPES, ...CYCLING_STEP_TYPES];
  return all.find((s) => s.value === type)?.label ?? type;
}

export const DURATION_TYPES: { value: DurationType; label: string }[] = [
  { value: "time", label: "Time" },
  { value: "distance", label: "Distance" },
  { value: "lap_button", label: "Lap button press" },
];

export function createEmptyStep(type: StepType): WorkoutStep {
  return {
    type,
    durationType: "time",
    duration: null,
    distance: null,
    targetType: null,
    targetMin: null,
    targetMax: null,
    targetZoneId: null,
    targetZoneName: null,
    notes: null,
  };
}

export function createEmptyRepeatBlock(): RepeatBlock {
  return {
    repeatCount: 3,
    steps: [createEmptyStep("interval"), createEmptyStep("recovery")],
  };
}

export type WorkoutTemplate = {
  id: string;
  label: string;
  sportCode: "running" | "cycling";
  workoutType: WorkoutType;
  title: string;
  steps: WorkoutStepItem[];
};
