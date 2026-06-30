import { useState } from "react";
import type { DurationType, WorkoutStep } from "./types";
import { DURATION_TYPES } from "./types";

const METERS_PER_MILE = 1609.344;
const METERS_PER_KM = 1000;

export type DistanceUnit = "mi" | "km" | "m";

export function minutesToHoursMinutes(totalMinutes: number): { hours: number; minutes: number } {
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return { hours, minutes };
}

export function hoursMinutesToMinutes(hours: number, minutes: number): number {
  return hours * 60 + minutes;
}

export function metersToDisplayValue(meters: number, unit: DistanceUnit): number {
  if (unit === "mi") return Math.round((meters / METERS_PER_MILE) * 100) / 100;
  if (unit === "km") return Math.round((meters / METERS_PER_KM) * 100) / 100;
  return meters;
}

export function displayValueToMeters(value: number, unit: DistanceUnit): number {
  if (unit === "mi") return Math.round(value * METERS_PER_MILE);
  if (unit === "km") return Math.round(value * METERS_PER_KM);
  return Math.round(value);
}

export function bestDistanceUnit(meters: number): DistanceUnit {
  if (meters >= METERS_PER_MILE && meters % METERS_PER_MILE === 0) return "mi";
  if (meters >= METERS_PER_KM && meters % METERS_PER_KM === 0) return "km";
  if (meters >= 1000) return "km";
  return "m";
}

type DurationEditorProps = {
  step: WorkoutStep;
  onChange: (step: WorkoutStep) => void;
};

export function DurationEditor({ step, onChange }: DurationEditorProps) {
  const durationType: DurationType = step.durationType ?? "time";
  const [distanceUnit, setDistanceUnit] = useState<DistanceUnit>(() =>
    step.distance != null ? bestDistanceUnit(step.distance) : "km",
  );

  function update(patch: Partial<WorkoutStep>) {
    onChange({ ...step, ...patch });
  }

  function handleTypeChange(nextType: DurationType) {
    if (nextType === "time") {
      update({
        durationType: nextType,
        duration: step.duration ?? 15,
        distance: null,
      });
    } else if (nextType === "distance") {
      update({
        durationType: nextType,
        duration: null,
        distance: step.distance ?? 1000,
      });
    } else {
      update({
        durationType: nextType,
        duration: null,
        distance: null,
      });
    }
  }

  const { hours, minutes } =
    step.duration != null ? minutesToHoursMinutes(step.duration) : { hours: 0, minutes: 0 };

  const distanceDisplay =
    step.distance != null ? metersToDisplayValue(step.distance, distanceUnit) : "";

  return (
    <section className="step-section">
      <h4 className="step-section-title">Duration</h4>
      <div className="step-section-row">
        <label>
          Type
          <select
            value={durationType}
            onChange={(e) => handleTypeChange(e.target.value as DurationType)}
          >
            {DURATION_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </label>

        {durationType === "time" && (
          <label>
            Time
            <div className="time-input-group">
              <input
                type="number"
                min={0}
                max={23}
                value={hours}
                onChange={(e) => {
                  const h = Number.parseInt(e.target.value, 10) || 0;
                  const m = minutes;
                  const total = hoursMinutesToMinutes(h, m);
                  update({ duration: total > 0 ? total : null });
                }}
                aria-label="Hours"
              />
              <span className="time-separator">:</span>
              <input
                type="number"
                min={0}
                max={59}
                value={minutes}
                onChange={(e) => {
                  const m = Number.parseInt(e.target.value, 10) || 0;
                  const h = hours;
                  const total = hoursMinutesToMinutes(h, Math.min(59, m));
                  update({ duration: total > 0 ? total : null });
                }}
                aria-label="Minutes"
              />
            </div>
            <span className="muted input-hint">hh:mm</span>
          </label>
        )}

        {durationType === "distance" && (
          <label>
            Distance
            <div className="distance-input-group">
              <input
                type="number"
                min={distanceUnit === "m" ? 1 : 0.01}
                step={distanceUnit === "m" ? 1 : 0.01}
                value={distanceDisplay}
                onChange={(e) => {
                  const raw = e.target.value;
                  if (!raw) {
                    update({ distance: null });
                    return;
                  }
                  const num = Number.parseFloat(raw);
                  if (Number.isNaN(num)) return;
                  update({ distance: displayValueToMeters(num, distanceUnit) });
                }}
              />
              <select
                value={distanceUnit}
                onChange={(e) => setDistanceUnit(e.target.value as DistanceUnit)}
                aria-label="Distance unit"
              >
                <option value="mi">mi</option>
                <option value="km">km</option>
                <option value="m">m</option>
              </select>
            </div>
          </label>
        )}

        {durationType === "lap_button" && (
          <div className="lap-button-hint">
            <span className="muted">Ends when athlete presses lap</span>
          </div>
        )}
      </div>
    </section>
  );
}
