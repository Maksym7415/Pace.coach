import { formatWorkoutPreview } from "./format";
import type { WorkoutStepItem } from "./types";

type WorkoutPreviewProps = {
  title: string;
  steps: WorkoutStepItem[];
  sportCode: string | null;
  durationMin: number | null;
  distanceM: number | null;
};

export function WorkoutPreview({
  title,
  steps,
  sportCode,
  durationMin,
  distanceM,
}: WorkoutPreviewProps) {
  const lines = formatWorkoutPreview(steps, sportCode, false);
  const meta = [
    durationMin != null ? `${durationMin} min` : null,
    distanceM != null ? `${(distanceM / 1000).toFixed(1)} km` : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className="workout-preview card stack">
      <h4>Preview</h4>
      <strong>{title || "Untitled workout"}</strong>
      {meta && <p className="muted">{meta}</p>}
      {lines.length === 0 ? (
        <p className="muted">Add steps to see a preview.</p>
      ) : (
        <ul className="workout-preview-list">
          {lines.map((line, index) => (
            <li key={index}>{line}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
