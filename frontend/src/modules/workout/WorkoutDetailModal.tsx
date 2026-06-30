import { formatActivityMeta } from "../activities/format";
import type { Workout } from "../training/api";
import { formatWorkoutPreview } from "./format";
import type { WorkoutStepItem } from "./types";

type WorkoutDetailModalProps = {
  workout: Workout;
  onClose: () => void;
  coachActions?: {
    onEdit: () => void;
    onDelete: () => void;
  };
};

function formatWorkoutType(type: string): string {
  return type.replace(/_/g, " ");
}

export function WorkoutDetailModal({ workout, onClose, coachActions }: WorkoutDetailModalProps) {
  const steps = workout.steps as WorkoutStepItem[] | null;
  const previewLines = formatWorkoutPreview(steps, workout.sport_code, false);
  const sportLabel = workout.sport_name ?? workout.sport_code;
  const distance =
    workout.distance_m != null ? `${(workout.distance_m / 1000).toFixed(1)} km` : null;
  const duration = workout.duration_min != null ? `${workout.duration_min} min` : null;
  const meta = [
    sportLabel,
    formatWorkoutType(workout.workout_type),
    workout.status,
    duration,
    distance,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal card stack workout-detail-modal" onClick={(e) => e.stopPropagation()}>
        <div className="row-between">
          <h3>{workout.title}</h3>
          <button type="button" className="secondary" onClick={onClose}>
            Close
          </button>
        </div>
        <p className="muted">
          {workout.scheduled_date} · {meta}
        </p>
        {workout.description && <p>{workout.description}</p>}

        <div className="stack">
          <h4>Steps</h4>
          {previewLines.length === 0 ? (
            <p className="muted">No steps defined.</p>
          ) : (
            <ul className="workout-steps workout-preview-list">
              {previewLines.map((line, index) => (
                <li key={index}>{line}</li>
              ))}
            </ul>
          )}
        </div>

        {workout.linked_activity && (
          <div className="linked-activity">
            <p className="muted">
              <strong>Completed activity:</strong> {workout.linked_activity.name} ·{" "}
              {formatActivityMeta(workout.linked_activity)}
            </p>
          </div>
        )}

        {coachActions && (
          <div className="workout-detail-actions row-between">
            <button
              type="button"
              className="secondary"
              onClick={() => {
                onClose();
                coachActions.onEdit();
              }}
            >
              Edit
            </button>
            <button
              type="button"
              className="secondary"
              onClick={() => {
                onClose();
                coachActions.onDelete();
              }}
            >
              Delete
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
