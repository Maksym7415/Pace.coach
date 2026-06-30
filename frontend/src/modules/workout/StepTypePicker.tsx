import { createEmptyRepeatBlock, createEmptyStep, stepTypesForSport, type StepType } from "./types";

type StepTypePickerProps = {
  sportCode: string | null;
  onAddStep: (type: StepType) => void;
  onAddRepeat: () => void;
};

export function StepTypePicker({ sportCode, onAddStep, onAddRepeat }: StepTypePickerProps) {
  const types = stepTypesForSport(sportCode);

  return (
    <div className="step-type-picker row-between">
      <div className="step-type-picker-buttons">
        {types.map((t) => (
          <button
            key={t.value}
            type="button"
            className="secondary"
            onClick={() => onAddStep(t.value)}
          >
            + {t.label}
          </button>
        ))}
      </div>
      <button type="button" className="secondary" onClick={onAddRepeat}>
        + Repeat block
      </button>
    </div>
  );
}

export function defaultStepForType(type: StepType) {
  const step = createEmptyStep(type);
  if (type === "warmup" || type === "cooldown") {
    step.durationType = "time";
    step.duration = 10;
  }
  if (type === "interval") {
    step.durationType = "distance";
    step.distance = 800;
  }
  if (type === "recovery" || type === "recovery_ride") {
    step.durationType = "time";
    step.duration = 2;
  }
  if (type === "run" || type === "ride") {
    step.durationType = "time";
    step.duration = 30;
  }
  return step;
}

export function defaultRepeatBlock() {
  return createEmptyRepeatBlock();
}
