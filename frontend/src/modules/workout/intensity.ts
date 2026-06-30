import type { Zone } from "../athlete-profile/api";
import type { TargetType, WorkoutStep } from "./types";

export type IntensityTargetKind =
  | "no_target"
  | "pace"
  | "cadence"
  | "hr_zone"
  | "hr_custom"
  | "power_zone"
  | "power_custom";

export const INTENSITY_OPTIONS: { value: IntensityTargetKind; label: string; sports: string[] }[] = [
  { value: "no_target", label: "No Target", sports: ["running", "cycling"] },
  { value: "pace", label: "Pace", sports: ["running"] },
  { value: "cadence", label: "Cadence", sports: ["running", "cycling"] },
  { value: "hr_zone", label: "Heart Rate Zone", sports: ["running", "cycling"] },
  { value: "hr_custom", label: "Custom Heart Rate", sports: ["running", "cycling"] },
  { value: "power_zone", label: "Power Zone", sports: ["cycling"] },
  { value: "power_custom", label: "Custom Power", sports: ["cycling"] },
];

export function intensityOptionsForSport(sportCode: string | null | undefined) {
  const code = sportCode === "cycling" ? "cycling" : "running";
  return INTENSITY_OPTIONS.filter((o) => o.sports.includes(code));
}

export function zonesForKind(kind: IntensityTargetKind, zones: Zone[]): Zone[] {
  if (kind === "hr_zone" || kind === "hr_custom") {
    return zones.filter((z) => z.zone_category === "hr");
  }
  if (kind === "power_zone" || kind === "power_custom") {
    return zones.filter((z) => z.zone_category === "power");
  }
  return [];
}

export function isIntensityOptionDisabled(kind: IntensityTargetKind, zones: Zone[]): boolean {
  if (kind === "hr_zone") return zonesForKind(kind, zones).length === 0;
  if (kind === "power_zone") return zonesForKind(kind, zones).length === 0;
  return false;
}

function zonePatchFromZone(zone: Zone): Partial<WorkoutStep> {
  return {
    targetZoneId: zone.id,
    targetZoneName: zone.zone_name,
    targetMin: zone.min_value,
    targetMax: zone.max_value,
  };
}

export function intensityKindFromStep(step: WorkoutStep): IntensityTargetKind {
  if (!step.targetType) return "no_target";
  if (step.targetType === "pace") return "pace";
  if (step.targetType === "cadence") return "cadence";
  if (step.targetType === "heart_rate") {
    return step.targetZoneId != null ? "hr_zone" : "hr_custom";
  }
  if (step.targetType === "power") {
    return step.targetZoneId != null ? "power_zone" : "power_custom";
  }
  return "no_target";
}

export function applyIntensityKind(kind: IntensityTargetKind): Partial<WorkoutStep> {
  if (kind === "no_target") {
    return {
      targetType: null,
      targetMin: null,
      targetMax: null,
      targetZoneId: null,
      targetZoneName: null,
    };
  }

  const base = {
    targetMin: null,
    targetMax: null,
    targetZoneId: null,
    targetZoneName: null,
  };

  switch (kind) {
    case "pace":
      return { ...base, targetType: "pace" as TargetType };
    case "cadence":
      return { ...base, targetType: "cadence" as TargetType };
    case "hr_zone":
      return { ...base, targetType: "heart_rate" as TargetType };
    case "hr_custom":
      return { ...base, targetType: "heart_rate" as TargetType };
    case "power_zone":
      return { ...base, targetType: "power" as TargetType };
    case "power_custom":
      return { ...base, targetType: "power" as TargetType };
    default:
      return { ...base, targetType: null };
  }
}

export function applyIntensityKindWithZones(
  kind: IntensityTargetKind,
  zones: Zone[],
): Partial<WorkoutStep> {
  const patch = applyIntensityKind(kind);

  if (kind === "hr_zone") {
    const hrZones = zonesForKind(kind, zones);
    if (hrZones.length > 0) {
      return { ...patch, ...zonePatchFromZone(hrZones[0]) };
    }
  }

  if (kind === "power_zone") {
    const powerZones = zonesForKind(kind, zones);
    if (powerZones.length > 0) {
      return { ...patch, ...zonePatchFromZone(powerZones[0]) };
    }
  }

  return patch;
}
