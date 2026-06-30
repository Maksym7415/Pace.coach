import type { SportProfile, Zone } from "../athlete-profile/api";
import { formatStepSummary } from "./format";
import { DurationEditor } from "./DurationEditor";
import { TargetEditor } from "./TargetEditor";
import type { WorkoutStep } from "./types";
import { stepTypeLabel } from "./types";

type WorkoutStepCardProps = {
  step: WorkoutStep;
  sportCode: string | null;
  zones: Zone[];
  profile: SportProfile | null;
  onChange: (step: WorkoutStep) => void;
  onRemove: () => void;
  onMoveUp?: () => void;
  onMoveDown?: () => void;
  dragHandle?: React.ReactNode;
};

export function WorkoutStepCard({
  step,
  sportCode,
  zones,
  profile,
  onChange,
  onRemove,
  onMoveUp,
  onMoveDown,
  dragHandle,
}: WorkoutStepCardProps) {
  return (
    <div className="workout-step-card card stack">
      <div className="workout-step-card-header row-between">
        <div className="row-between" style={{ gap: "0.5rem", alignItems: "center" }}>
          {dragHandle}
          <strong>{stepTypeLabel(step.type)}</strong>
        </div>
        <div className="step-actions">
          {onMoveUp && (
            <button type="button" className="secondary" onClick={onMoveUp} aria-label="Move up">
              ↑
            </button>
          )}
          {onMoveDown && (
            <button type="button" className="secondary" onClick={onMoveDown} aria-label="Move down">
              ↓
            </button>
          )}
          <button type="button" className="secondary" onClick={onRemove}>
            Remove
          </button>
        </div>
      </div>

      <p className="muted step-summary-preview">{formatStepSummary(step, sportCode)}</p>

      <DurationEditor step={step} onChange={onChange} />

      <TargetEditor
        step={step}
        sportCode={sportCode}
        zones={zones}
        profile={profile}
        onChange={onChange}
      />

      <label>
        Step notes
        <input
          value={step.notes ?? ""}
          onChange={(e) => onChange({ ...step, notes: e.target.value || null })}
        />
      </label>
    </div>
  );
}
