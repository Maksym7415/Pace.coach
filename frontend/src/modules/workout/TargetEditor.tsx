import { useEffect, useState } from "react";
import type { SportProfile, Zone, ZoneCategory } from "../athlete-profile/api";
import { mmssToSecs, secsToMMSS } from "../athlete-profile/api";
import {
  applyIntensityKindWithZones,
  intensityKindFromStep,
  intensityOptionsForSport,
  isIntensityOptionDisabled,
  zonesForKind,
  type IntensityTargetKind,
} from "./intensity";
import type { WorkoutStep } from "./types";

type TargetEditorProps = {
  step: WorkoutStep;
  sportCode: string | null;
  zones: Zone[];
  profile: SportProfile | null;
  onChange: (step: WorkoutStep) => void;
};

function zoneUnitLabel(category: ZoneCategory): string {
  if (category === "hr") return "bpm";
  if (category === "power") return "W";
  return "";
}

function secsToPaceString(secs: number | null): string {
  if (secs == null) return "";
  return secsToMMSS(Math.round(secs));
}

type PaceRangeInputsProps = {
  targetMin: number | null;
  targetMax: number | null;
  onChange: (patch: Pick<WorkoutStep, "targetMin" | "targetMax" | "targetZoneId" | "targetZoneName">) => void;
};

function PaceRangeInputs({ targetMin, targetMax, onChange }: PaceRangeInputsProps) {
  const [minDraft, setMinDraft] = useState(() => secsToPaceString(targetMin));
  const [maxDraft, setMaxDraft] = useState(() => secsToPaceString(targetMax));

  useEffect(() => {
    setMinDraft(secsToPaceString(targetMin));
  }, [targetMin]);

  useEffect(() => {
    setMaxDraft(secsToPaceString(targetMax));
  }, [targetMax]);

  function commitPace(
    field: "targetMin" | "targetMax",
    value: string,
    setDraft: (next: string) => void,
  ) {
    const trimmed = value.trim();
    if (!trimmed) {
      setDraft("");
      onChange({ [field]: null, targetZoneId: null, targetZoneName: null });
      return;
    }
    const secs = mmssToSecs(trimmed);
    if (secs != null) {
      setDraft(secsToMMSS(secs));
      onChange({ [field]: secs, targetZoneId: null, targetZoneName: null });
    }
  }

  function handleChange(
    field: "targetMin" | "targetMax",
    value: string,
    setDraft: (next: string) => void,
  ) {
    setDraft(value);
    const secs = mmssToSecs(value);
    if (secs != null) {
      onChange({ [field]: secs, targetZoneId: null, targetZoneName: null });
    } else if (!value.trim()) {
      onChange({ [field]: null, targetZoneId: null, targetZoneName: null });
    }
  }

  function handleBlur(
    field: "targetMin" | "targetMax",
    value: string,
    storedSecs: number | null,
    setDraft: (next: string) => void,
  ) {
    const trimmed = value.trim();
    if (!trimmed) {
      setDraft("");
      onChange({ [field]: null, targetZoneId: null, targetZoneName: null });
      return;
    }
    if (mmssToSecs(trimmed) != null) {
      commitPace(field, trimmed, setDraft);
      return;
    }
    setDraft(secsToPaceString(storedSecs));
  }

  return (
    <div className="range-input-group pace-input">
      <input
        type="text"
        placeholder="m:ss"
        value={minDraft}
        onChange={(e) => handleChange("targetMin", e.target.value, setMinDraft)}
        onBlur={(e) => handleBlur("targetMin", e.target.value, targetMin, setMinDraft)}
        aria-label="Pace minimum"
      />
      <span className="range-separator">to</span>
      <input
        type="text"
        placeholder="m:ss"
        value={maxDraft}
        onChange={(e) => handleChange("targetMax", e.target.value, setMaxDraft)}
        onBlur={(e) => handleBlur("targetMax", e.target.value, targetMax, setMaxDraft)}
        aria-label="Pace maximum"
      />
      <span className="range-unit">min/km</span>
    </div>
  );
}

export function TargetEditor({ step, sportCode, zones, profile, onChange }: TargetEditorProps) {
  const kind = intensityKindFromStep(step);
  const options = intensityOptionsForSport(sportCode);
  const filteredZones = zonesForKind(kind, zones);

  function update(patch: Partial<WorkoutStep>) {
    onChange({ ...step, ...patch });
  }

  function handleKindChange(nextKind: IntensityTargetKind) {
    if (isIntensityOptionDisabled(nextKind, zones)) return;
    update(applyIntensityKindWithZones(nextKind, zones));
  }

  function applyZone(zoneId: string) {
    if (!zoneId) {
      update({ targetZoneId: null, targetZoneName: null, targetMin: null, targetMax: null });
      return;
    }
    const zone = filteredZones.find((z) => z.id === Number(zoneId));
    if (!zone) return;
    update({
      targetZoneId: zone.id,
      targetZoneName: zone.zone_name,
      targetMin: zone.min_value,
      targetMax: zone.max_value,
    });
  }

  return (
    <section className="step-section">
      <h4 className="step-section-title">Intensity Target</h4>
      <div className="step-section-row">
        <label>
          Type
          <select value={kind} onChange={(e) => handleKindChange(e.target.value as IntensityTargetKind)}>
            {options.map((o) => {
              const disabled = isIntensityOptionDisabled(o.value, zones);
              return (
                <option key={o.value} value={o.value} disabled={disabled}>
                  {o.label}
                  {disabled ? " (not configured)" : ""}
                </option>
              );
            })}
          </select>
        </label>

        {kind === "pace" && (
          <label>
            Pace
            <PaceRangeInputs
              targetMin={step.targetMin}
              targetMax={step.targetMax}
              onChange={(patch) => update(patch)}
            />
          </label>
        )}

        {kind === "cadence" && (
          <label>
            Cadence
            <div className="range-input-group">
              <input
                type="number"
                min={1}
                value={step.targetMin ?? ""}
                onChange={(e) =>
                  update({
                    targetMin: e.target.value ? Number(e.target.value) : null,
                    targetZoneId: null,
                    targetZoneName: null,
                  })
                }
                aria-label="Cadence minimum"
              />
              <span className="range-separator">to</span>
              <input
                type="number"
                min={1}
                value={step.targetMax ?? ""}
                onChange={(e) =>
                  update({
                    targetMax: e.target.value ? Number(e.target.value) : null,
                    targetZoneId: null,
                    targetZoneName: null,
                  })
                }
                aria-label="Cadence maximum"
              />
              <span className="range-unit">{sportCode === "cycling" ? "rpm" : "spm"}</span>
            </div>
          </label>
        )}

        {(kind === "hr_zone" || kind === "power_zone") && filteredZones.length > 0 && (
          <label>
            {kind === "hr_zone" ? "Heart Rate Target" : "Power Target"}
            <select
              value={step.targetZoneId ?? ""}
              onChange={(e) => applyZone(e.target.value)}
            >
              <option value="">Select zone</option>
              {filteredZones.map((zone) => (
                <option key={zone.id} value={zone.id}>
                  {zone.zone_name} ({zone.min_value}–{zone.max_value}{" "}
                  {zoneUnitLabel(zone.zone_category)})
                </option>
              ))}
            </select>
          </label>
        )}

        {(kind === "hr_custom" || kind === "power_custom") && (
          <label>
            Target
            <div className="range-input-group">
              <input
                type="number"
                min={1}
                value={step.targetMin ?? ""}
                onChange={(e) =>
                  update({
                    targetMin: e.target.value ? Number(e.target.value) : null,
                    targetZoneId: null,
                    targetZoneName: null,
                  })
                }
                aria-label="Target minimum"
              />
              <span className="range-separator">to</span>
              <input
                type="number"
                min={1}
                value={step.targetMax ?? ""}
                onChange={(e) =>
                  update({
                    targetMax: e.target.value ? Number(e.target.value) : null,
                    targetZoneId: null,
                    targetZoneName: null,
                  })
                }
                aria-label="Target maximum"
              />
              <span className="range-unit">{kind === "hr_custom" ? "bpm" : "W"}</span>
            </div>
            {kind === "power_custom" &&
              profile &&
              sportCode === "cycling" &&
              profile.ftp_watts && (
                <button
                  type="button"
                  className="secondary quick-fill-btn"
                  onClick={() =>
                    update({
                      targetMin: Math.round(profile.ftp_watts! * 0.88),
                      targetMax: Math.round(profile.ftp_watts! * 0.93),
                      targetZoneId: null,
                      targetZoneName: "Sweet spot",
                    })
                  }
                >
                  Fill 88–93% FTP ({profile.ftp_watts} W)
                </button>
              )}
            {kind === "hr_custom" &&
              profile &&
              sportCode === "running" &&
              profile.threshold_hr && (
                <button
                  type="button"
                  className="secondary quick-fill-btn"
                  onClick={() =>
                    update({
                      targetMin: Math.round(profile.threshold_hr! * 0.85),
                      targetMax: profile.threshold_hr,
                      targetZoneId: null,
                      targetZoneName: "Threshold HR",
                    })
                  }
                >
                  Fill threshold HR ({profile.threshold_hr} bpm)
                </button>
              )}
          </label>
        )}
      </div>
    </section>
  );
}
