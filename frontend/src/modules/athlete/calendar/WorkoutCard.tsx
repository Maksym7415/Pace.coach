import type { Workout } from "../../training/api";
import { formatActivityMeta } from "../../activities/format";

type WorkoutCardProps = {
  workout: Workout;
  compact?: boolean;
  onSelect?: () => void;
};

function formatWorkoutType(type: string): string {
  return type.replace(/_/g, " ");
}

function formatDistance(meters: number | null): string | null {
  if (meters === null) return null;
  return `${(meters / 1000).toFixed(1)} km`;
}

export function WorkoutCard({ workout, compact = false, onSelect }: WorkoutCardProps) {
  const distance = formatDistance(workout.distance_m);
  const duration = workout.duration_min ? `${workout.duration_min} min` : null;
  const meta = [formatWorkoutType(workout.workout_type), workout.status, duration, distance]
    .filter(Boolean)
    .join(" · ");

  return (
    <article
      className={`workout-card ${compact ? "workout-card-compact" : ""}`}
      onClick={onSelect}
      onKeyDown={
        onSelect
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") onSelect();
            }
          : undefined
      }
      role={onSelect ? "button" : undefined}
      tabIndex={onSelect ? 0 : undefined}
    >
      <div className="row-between">
        <strong>{workout.title}</strong>
        <span className={`status-badge status-${workout.status}`}>{workout.status}</span>
      </div>
      <p className="muted">{meta}</p>
      {!compact && workout.description && <p>{workout.description}</p>}
      {!compact && Array.isArray(workout.steps) && workout.steps.length > 0 && (
        <ol className="workout-steps">
          {(workout.steps as unknown[]).map((step, index) => (
            <li key={index}>
              {typeof step === "object" && step !== null
                ? JSON.stringify(step)
                : String(step)}
            </li>
          ))}
        </ol>
      )}
      {workout.linked_activity && (
        <div className="linked-activity">
          <p className="muted">
            <strong>Completed:</strong> {workout.linked_activity.name} ·{" "}
            {formatActivityMeta(workout.linked_activity)}
          </p>
        </div>
      )}
    </article>
  );
}
