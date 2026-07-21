import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { importFitFile } from "../activities/api";
import { useAuth } from "../auth/AuthContext";
import { getCalendar, type Workout } from "../training/api";
import { WorkoutDetailModal } from "../workout/WorkoutDetailModal";
import { todayIso } from "../shared/dates";
import { WorkoutCard } from "./calendar/WorkoutCard";

export function TodayWorkoutCard() {
  const { user } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [workouts, setWorkouts] = useState<Workout[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Workout | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  useEffect(() => {
    const today = todayIso();
    getCalendar(today, today).then((result) => {
      if (!result.success) {
        setError(result.error ?? "Failed to load today's workouts");
      } else {
        setWorkouts(result.workouts);
      }
      setLoading(false);
    });
  }, []);

  async function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !user) return;

    if (!file.name.toLowerCase().endsWith(".fit")) {
      setUploadError("Please select a .fit file");
      setUploadSuccess(null);
      return;
    }

    setUploading(true);
    setUploadError(null);
    setUploadSuccess(null);

    try {
      const result = await importFitFile(user.id, file);
      if (!result.success) {
        setUploadError(result.error ?? "Failed to upload activity");
      } else {
        setUploadSuccess("Activity uploaded — processing in background.");
      }
    } catch {
      setUploadError("Failed to upload activity");
    } finally {
      setUploading(false);
    }
  }

  if (loading) return <p className="muted">Loading today's workouts…</p>;
  if (error) return <p className="error">{error}</p>;

  const heading =
    workouts.length > 1 ? `Today's workouts (${workouts.length})` : "Today's workout";

  return (
    <div className="stack">
      <h3>{heading}</h3>
      {workouts.length === 0 ? (
        <p className="muted">No workout planned today.</p>
      ) : (
        workouts.map((workout) => (
          <WorkoutCard
            key={workout.id}
            workout={workout}
            compact
            onSelect={() => setSelected(workout)}
          />
        ))
      )}

      <input
        ref={fileInputRef}
        type="file"
        accept=".fit"
        hidden
        onChange={handleFileChange}
      />
      <button
        type="button"
        disabled={uploading || !user}
        onClick={() => fileInputRef.current?.click()}
      >
        {uploading ? "Uploading…" : "Upload activity"}
      </button>
      {uploadError && <p className="error">{uploadError}</p>}
      {uploadSuccess && <p className="muted">{uploadSuccess}</p>}

      {selected && (
        <WorkoutDetailModal workout={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}
