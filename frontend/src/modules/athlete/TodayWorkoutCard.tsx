import { useEffect, useState } from "react";
import { getCalendar, type Workout } from "../training/api";
import { WorkoutDetailModal } from "../workout/WorkoutDetailModal";
import { todayIso } from "../shared/dates";
import { WorkoutCard } from "./calendar/WorkoutCard";

export function TodayWorkoutCard() {
  const [workouts, setWorkouts] = useState<Workout[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Workout | null>(null);

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
      {selected && (
        <WorkoutDetailModal workout={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}
