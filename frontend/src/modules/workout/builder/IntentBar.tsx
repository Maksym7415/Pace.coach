import { WORKOUT_TYPES, type WorkoutType } from "../../training/api";

type IntentBarProps = {
  purpose: string;
  sportId: number | null;
  sports: { id: number; name: string; code: string }[];
  workoutType: WorkoutType;
  targetRpe: number | null;
  title: string;
  onPurposeChange: (value: string) => void;
  onSportChange: (sportId: number) => void;
  onWorkoutTypeChange: (type: WorkoutType) => void;
  onTargetRpeChange: (value: number | null) => void;
  onTitleChange: (value: string) => void;
};

export function IntentBar({
  purpose,
  sportId,
  sports,
  workoutType,
  targetRpe,
  title,
  onPurposeChange,
  onSportChange,
  onWorkoutTypeChange,
  onTargetRpeChange,
  onTitleChange,
}: IntentBarProps) {
  return (
    <div className="builder-intent card stack">
      <div className="row-between">
        <h3>Intent</h3>
        <span className="muted">required before structure</span>
      </div>
      <div className="form-grid">
        <label>
          Purpose
          <input
            value={purpose}
            onChange={(e) => onPurposeChange(e.target.value)}
            placeholder="e.g. Threshold development"
          />
        </label>
        <label>
          Sport
          <select
            value={sportId ?? ""}
            onChange={(e) => onSportChange(Number(e.target.value))}
            required
          >
            {sports.map((sport) => (
              <option key={sport.id} value={sport.id}>
                {sport.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Workout type
          <select
            value={workoutType}
            onChange={(e) => onWorkoutTypeChange(e.target.value as WorkoutType)}
          >
            {WORKOUT_TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Target RPE
          <input
            type="number"
            min={1}
            max={10}
            value={targetRpe ?? ""}
            onChange={(e) => {
              const raw = e.target.value;
              if (!raw) {
                onTargetRpeChange(null);
                return;
              }
              const n = Number.parseInt(raw, 10);
              onTargetRpeChange(Number.isNaN(n) ? null : Math.min(10, Math.max(1, n)));
            }}
            placeholder="1–10"
          />
        </label>
        <label>
          Title
          <input value={title} onChange={(e) => onTitleChange(e.target.value)} required />
        </label>
      </div>
    </div>
  );
}
