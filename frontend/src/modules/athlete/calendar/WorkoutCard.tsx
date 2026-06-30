import type { Workout } from "../../training/api";
import { formatActivityMeta } from "../../activities/format";
import { formatWorkoutPreview } from "../../workout/format";
import type { WorkoutStepItem } from "../../workout/types";

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

export function WorkoutCard({
  workout,
  compact = false,
  onSelect,
}: WorkoutCardProps) {
  const distance = formatDistance(workout.distance_m);
  const duration = workout.duration_min ? `${workout.duration_min} min` : null;
  const sportLabel = workout.sport_name ?? workout.sport_code;
  const meta = [
    sportLabel,
    formatWorkoutType(workout.workout_type),
    workout.status,
    duration,
    distance,
  ]
    .filter(Boolean)
    .join(" · ");

  const steps = workout.steps as WorkoutStepItem[] | null;
  const previewLines = formatWorkoutPreview(steps, workout.sport_code, compact);

  return (
    <article
      className={`workout-card ${compact ? "workout-card-compact" : ""} ${
        onSelect ? "workout-card-clickable" : ""
      }`}
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
      {!compact && previewLines.length > 0 && (
        <ul className="workout-steps workout-preview-list">
          {previewLines.map((line, index) => (
            <li key={index}>{line}</li>
          ))}
        </ul>
      )}
      {compact && previewLines.length > 0 && <p className="muted">{previewLines[0]}</p>}
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
