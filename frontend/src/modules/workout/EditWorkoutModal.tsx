import { useEffect, useState } from "react";
import { getWorkout, type Workout } from "../training/api";
import { WorkoutBuilder } from "./WorkoutBuilder";
import { updateWorkout } from "../training/api";

type EditWorkoutModalProps = {
  workoutId: number;
  athleteId: number;
  onClose: () => void;
  onSaved: () => void;
};

export function EditWorkoutModal({ workoutId, athleteId, onClose, onSaved }: EditWorkoutModalProps) {
  const [workout, setWorkout] = useState<Workout | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getWorkout(workoutId).then((result) => {
      if (!result.success || !result.workout) {
        setError(result.error ?? "Failed to load workout");
      } else {
        setWorkout(result.workout);
      }
      setLoading(false);
    });
  }, [workoutId]);

  if (loading) {
    return (
      <div className="modal-backdrop" onClick={onClose}>
        <div className="modal card" onClick={(e) => e.stopPropagation()}>
          <p className="muted">Loading workout…</p>
        </div>
      </div>
    );
  }

  if (error || !workout) {
    return (
      <div className="modal-backdrop" onClick={onClose}>
        <div className="modal card" onClick={(e) => e.stopPropagation()}>
          <p className="error">{error ?? "Workout not found"}</p>
          <button type="button" className="secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal card workout-edit-modal" onClick={(e) => e.stopPropagation()}>
        <WorkoutBuilder
          athleteId={athleteId}
          mode="edit"
          initialWorkout={workout}
          onCancel={onClose}
          onSubmit={async (payload) => {
            const result = await updateWorkout(workoutId, payload);
            if (result.success) {
              onSaved();
              onClose();
            }
            return { success: result.success, error: result.error };
          }}
        />
      </div>
    </div>
  );
}
