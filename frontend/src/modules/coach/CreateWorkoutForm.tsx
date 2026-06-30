import { useState } from "react";
import { createWorkout } from "../training/api";
import { WorkoutBuilder } from "../workout/WorkoutBuilder";

type CreateWorkoutFormProps = {
  athleteId: number;
  onCreated?: () => void;
};

export function CreateWorkoutForm({ athleteId, onCreated }: CreateWorkoutFormProps) {
  const [success, setSuccess] = useState<string | null>(null);
  const [formKey, setFormKey] = useState(0);

  return (
    <>
      <WorkoutBuilder
        key={formKey}
        athleteId={athleteId}
        mode="create"
        onSubmit={async (payload) => {
          const result = await createWorkout({
            athlete_id: athleteId,
            ...payload,
          });
          if (result.success) {
            setSuccess("Workout scheduled");
            setFormKey((k) => k + 1);
            onCreated?.();
          }
          return { success: result.success, error: result.error };
        }}
      />
      {success && <p className="success">{success}</p>}
    </>
  );
}
