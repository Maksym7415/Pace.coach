import type { SportProfile, Zone } from "../athlete-profile/api";
import { WorkoutStepCard } from "./WorkoutStepCard";
import { defaultStepForType } from "./StepTypePicker";
import type { RepeatBlock, WorkoutStep } from "./types";
import { stepTypesForSport } from "./types";

type RepeatBlockEditorProps = {
  block: RepeatBlock;
  sportCode: string | null;
  zones: Zone[];
  profile: SportProfile | null;
  onChange: (block: RepeatBlock) => void;
  onRemove: () => void;
  onMoveUp?: () => void;
  onMoveDown?: () => void;
  dragHandle?: React.ReactNode;
};

export function RepeatBlockEditor({
  block,
  sportCode,
  zones,
  profile,
  onChange,
  onRemove,
  onMoveUp,
  onMoveDown,
  dragHandle,
}: RepeatBlockEditorProps) {
  const stepTypes = stepTypesForSport(sportCode);

  function updateStep(index: number, step: WorkoutStep) {
    const steps = [...block.steps];
    steps[index] = step;
    onChange({ ...block, steps });
  }

  function addStep() {
    onChange({
      ...block,
      steps: [...block.steps, defaultStepForType("recovery")],
    });
  }

  return (
    <div className="repeat-block card stack">
      <div className="workout-step-card-header row-between">
        <div className="row-between" style={{ gap: "0.5rem", alignItems: "center" }}>
          {dragHandle}
          <strong>Repeat block</strong>
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

      <label>
        Repeat count
        <input
          type="number"
          min={1}
          value={block.repeatCount}
          onChange={(e) =>
            onChange({
              ...block,
              repeatCount: Math.max(1, Number.parseInt(e.target.value, 10) || 1),
            })
          }
        />
      </label>

      <div className="stack">
        {block.steps.map((step, index) => (
          <div key={index} className="repeat-block-step">
            <label>
              Step type
              <select
                value={step.type}
                onChange={(e) =>
                  updateStep(index, { ...step, type: e.target.value as WorkoutStep["type"] })
                }
              >
                {stepTypes.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </label>
            <WorkoutStepCard
              step={step}
              sportCode={sportCode}
              zones={zones}
              profile={profile}
              onChange={(updated) => updateStep(index, updated)}
              onRemove={() => {
                if (block.steps.length <= 1) return;
                onChange({
                  ...block,
                  steps: block.steps.filter((_, i) => i !== index),
                });
              }}
            />
          </div>
        ))}
      </div>

      <button type="button" className="secondary" onClick={addStep}>
        + Add step to repeat
      </button>
    </div>
  );
}
