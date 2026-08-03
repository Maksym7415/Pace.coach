import type { SportProfile, Zone } from "../../athlete-profile/api";
import { formatStepSummary } from "../format";
import { DurationEditor } from "../DurationEditor";
import { TargetEditor } from "../TargetEditor";
import type { RepeatBlock, WorkoutStep, WorkoutStepItem } from "../types";
import { isRepeatBlock, stepTypeLabel, stepTypesForSport } from "../types";
import { defaultStepForType } from "../StepTypePicker";

type InspectorPaneProps = {
  item: WorkoutStepItem | null;
  sportCode: string | null;
  zones: Zone[];
  profile: SportProfile | null;
  onChange: (item: WorkoutStepItem) => void;
  onRemove: () => void;
  onDuplicate: () => void;
};

export function InspectorPane({
  item,
  sportCode,
  zones,
  profile,
  onChange,
  onRemove,
  onDuplicate,
}: InspectorPaneProps) {
  if (!item) {
    return (
      <div className="builder-pane builder-inspector card stack">
        <div className="row-between">
          <h3>Inspector</h3>
          <span className="muted">selected step</span>
        </div>
        <p className="muted">Select a step on the canvas to edit its details.</p>
      </div>
    );
  }

  if (isRepeatBlock(item)) {
    return (
      <div className="builder-pane builder-inspector card stack">
        <div className="row-between">
          <h3>Repeat block</h3>
          <div className="step-actions">
            <button type="button" className="secondary" onClick={onDuplicate}>
              Duplicate
            </button>
            <button type="button" className="secondary" onClick={onRemove}>
              Delete
            </button>
          </div>
        </div>

        <label>
          Repeat count
          <input
            type="number"
            min={1}
            value={item.repeatCount}
            onChange={(e) =>
              onChange({
                ...item,
                repeatCount: Math.max(1, Number.parseInt(e.target.value, 10) || 1),
              })
            }
          />
        </label>

        <div className="stack">
          {item.steps.map((step, index) => (
            <div key={index} className="stack" style={{ borderTop: "1px solid #e2e8f0", paddingTop: "0.75rem" }}>
              <strong>{stepTypeLabel(step.type)}</strong>
              <DurationEditor
                step={step}
                onChange={(updated) => {
                  const steps = [...item.steps];
                  steps[index] = updated;
                  onChange({ ...item, steps });
                }}
              />
              <TargetEditor
                step={step}
                sportCode={sportCode}
                zones={zones}
                profile={profile}
                onChange={(updated) => {
                  const steps = [...item.steps];
                  steps[index] = updated;
                  onChange({ ...item, steps });
                }}
              />
              <label>
                Cue
                <input
                  value={step.notes ?? ""}
                  onChange={(e) => {
                    const steps = [...item.steps];
                    steps[index] = { ...step, notes: e.target.value || null };
                    onChange({ ...item, steps });
                  }}
                />
              </label>
              <button
                type="button"
                className="secondary"
                onClick={() =>
                  onChange({ ...item, steps: item.steps.filter((_, i) => i !== index) })
                }
                disabled={item.steps.length <= 1}
              >
                Remove step
              </button>
            </div>
          ))}
        </div>

        <button
          type="button"
          className="secondary"
          onClick={() =>
            onChange({
              ...item,
              steps: [...item.steps, defaultStepForType("recovery")],
            })
          }
        >
          + Add step in block
        </button>
      </div>
    );
  }

  const step = item as WorkoutStep;
  return (
      <div className="builder-pane builder-inspector card stack">
        <div className="row-between">
          <h3>Inspector · {stepTypeLabel(step.type)}</h3>
          <div className="step-actions">
            <button type="button" className="secondary" onClick={onDuplicate}>
              Duplicate
            </button>
            <button type="button" className="secondary" onClick={onRemove}>
              Delete
            </button>
          </div>
        </div>

        <p className="muted">{formatStepSummary(step, sportCode)}</p>

      <label>
        Step type
        <select
          value={step.type}
          onChange={(e) => onChange({ ...step, type: e.target.value as WorkoutStep["type"] })}
        >
          {stepTypesForSport(sportCode).map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
      </label>

      <DurationEditor step={step} onChange={onChange} />
      <TargetEditor
        step={step}
        sportCode={sportCode}
        zones={zones}
        profile={profile}
        onChange={onChange}
      />

      <label>
        Cue
        <input
          value={step.notes ?? ""}
          onChange={(e) => onChange({ ...step, notes: e.target.value || null })}
        />
      </label>
    </div>
  );
}

export function duplicateItem(item: WorkoutStepItem): WorkoutStepItem {
  if (isRepeatBlock(item)) {
    return structuredClone(item) as RepeatBlock;
  }
  return structuredClone(item) as WorkoutStep;
}
