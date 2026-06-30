import { useEffect, useMemo, useState } from "react";
import { deleteWorkout, getAthleteCalendar, type Workout } from "../../training/api";
import { formatMonthYear, monthBounds, toIsoDate } from "../../shared/dates";
import { CalendarDayEvents } from "../../athlete/calendar/CalendarDayEvents";
import { WorkoutCard } from "../../athlete/calendar/WorkoutCard";
import { EditWorkoutModal } from "../../workout/EditWorkoutModal";
import { WorkoutDetailModal } from "../../workout/WorkoutDetailModal";

function groupWorkoutsByDate(workouts: Workout[]): Map<string, Workout[]> {
  const map = new Map<string, Workout[]>();
  for (const workout of workouts) {
    const list = map.get(workout.scheduled_date) ?? [];
    list.push(workout);
    map.set(workout.scheduled_date, list);
  }
  return map;
}

function buildMonthGrid(year: number, month: number): (string | null)[] {
  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells: (string | null)[] = [];

  for (let i = 0; i < firstDay; i += 1) cells.push(null);
  for (let day = 1; day <= daysInMonth; day += 1) {
    cells.push(toIsoDate(year, month, day));
  }
  while (cells.length % 7 !== 0) cells.push(null);

  return cells;
}

type CoachMonthCalendarProps = {
  athleteId: number;
  refreshKey?: number;
};

export function CoachMonthCalendar({ athleteId, refreshKey = 0 }: CoachMonthCalendarProps) {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth());
  const [workouts, setWorkouts] = useState<Workout[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [selectedWorkout, setSelectedWorkout] = useState<Workout | null>(null);
  const [editingWorkoutId, setEditingWorkoutId] = useState<number | null>(null);

  useEffect(() => {
    setLoading(true);
    const { start, end } = monthBounds(year, month);
    getAthleteCalendar(athleteId, start, end).then((result) => {
      if (!result.success) {
        setError(result.error ?? "Failed to load calendar");
        setWorkouts([]);
      } else {
        setError(null);
        setWorkouts(result.workouts);
      }
      setLoading(false);
    });
  }, [athleteId, year, month, refreshKey]);

  const byDate = useMemo(() => groupWorkoutsByDate(workouts), [workouts]);
  const grid = useMemo(() => buildMonthGrid(year, month), [year, month]);
  const selectedWorkouts = selectedDate ? (byDate.get(selectedDate) ?? []) : [];

  function prevMonth() {
    if (month === 0) {
      setYear((y) => y - 1);
      setMonth(11);
    } else {
      setMonth((m) => m - 1);
    }
  }

  function nextMonth() {
    if (month === 11) {
      setYear((y) => y + 1);
      setMonth(0);
    } else {
      setMonth((m) => m + 1);
    }
  }

  async function handleDelete(workout: Workout) {
    if (!window.confirm(`Delete scheduled workout "${workout.title}"?`)) return;
    const result = await deleteWorkout(workout.id);
    if (!result.success) {
      setError(result.error ?? "Failed to delete workout");
      return;
    }
    setWorkouts((prev) => prev.filter((w) => w.id !== workout.id));
  }

  return (
    <div className="stack">
      <div className="row-between">
        <h3>Training calendar</h3>
        <div className="calendar-nav">
          <button type="button" className="secondary" onClick={prevMonth}>
            Prev
          </button>
          <span>{formatMonthYear(year, month)}</span>
          <button type="button" className="secondary" onClick={nextMonth}>
            Next
          </button>
        </div>
      </div>

      {loading && <p className="muted">Loading calendar…</p>}
      {error && <p className="error">{error}</p>}

      {!loading && !error && workouts.length === 0 && (
        <p className="muted">No workouts scheduled this month yet.</p>
      )}

      <div className="calendar-weekdays">
        {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => (
          <span key={day}>{day}</span>
        ))}
      </div>

      <div className="calendar-grid">
        {grid.map((iso, index) => {
          if (!iso) return <div key={`empty-${index}`} className="calendar-cell empty" />;
          const dayWorkouts = byDate.get(iso) ?? [];
          const dayNum = Number(iso.split("-")[2]);
          return (
            <button
              key={iso}
              type="button"
              className={`calendar-cell ${dayWorkouts.length ? "has-workout" : ""} ${
                selectedDate === iso ? "selected" : ""
              }`}
              onClick={() => setSelectedDate(iso)}
            >
              <span className="calendar-day">{dayNum}</span>
              {dayWorkouts.length > 0 && (
                <CalendarDayEvents
                  workouts={dayWorkouts}
                  activities={[]}
                  onWorkoutClick={(workoutId) => {
                    const workout = dayWorkouts.find((w) => w.id === workoutId);
                    if (workout) setSelectedWorkout(workout);
                  }}
                />
              )}
            </button>
          );
        })}
      </div>

      {selectedDate && (
        <div className="card stack">
          <h4>Workouts on {selectedDate}</h4>
          {selectedWorkouts.length === 0 ? (
            <p className="muted">No workouts scheduled.</p>
          ) : (
            selectedWorkouts.map((workout) => (
              <WorkoutCard
                key={workout.id}
                workout={workout}
                compact
                onSelect={() => setSelectedWorkout(workout)}
              />
            ))
          )}
        </div>
      )}

      {selectedWorkout && (
        <WorkoutDetailModal
          workout={selectedWorkout}
          onClose={() => setSelectedWorkout(null)}
          coachActions={
            selectedWorkout.status === "scheduled"
              ? {
                  onEdit: () => setEditingWorkoutId(selectedWorkout.id),
                  onDelete: () => handleDelete(selectedWorkout),
                }
              : undefined
          }
        />
      )}

      {editingWorkoutId != null && (
        <EditWorkoutModal
          workoutId={editingWorkoutId}
          athleteId={athleteId}
          onClose={() => setEditingWorkoutId(null)}
          onSaved={() => {
            const { start, end } = monthBounds(year, month);
            getAthleteCalendar(athleteId, start, end).then((result) => {
              if (result.success) setWorkouts(result.workouts);
            });
          }}
        />
      )}
    </div>
  );
}
