import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { listAthleteActivities, type Activity } from "../../activities/api";
import { deleteWorkout, getAthleteCalendar, type Workout } from "../../training/api";
import { formatMonthYear, monthBounds, toDateKey, toIsoDate } from "../../shared/dates";
import { ActivityCard } from "../../athlete/activities/ActivityCard";
import { CalendarDayEvents } from "../../athlete/calendar/CalendarDayEvents";
import { WorkoutCard } from "../../athlete/calendar/WorkoutCard";
import { WorkoutDetailModal } from "../../workout/WorkoutDetailModal";

function groupByDate<T extends { date?: string; scheduled_date?: string }>(
  items: T[],
  dateKey: "date" | "scheduled_date",
): Map<string, T[]> {
  const map = new Map<string, T[]>();
  for (const item of items) {
    const raw =
      dateKey === "date"
        ? (item as { date: string }).date
        : (item as { scheduled_date: string }).scheduled_date;
    const iso = toDateKey(raw);
    const list = map.get(iso) ?? [];
    list.push(item);
    map.set(iso, list);
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

function unlinkedActivitiesForDay(workouts: Workout[], activities: Activity[]): Activity[] {
  const linkedIds = new Set(
    workouts.map((w) => w.activity_id).filter((id): id is number => id !== null),
  );
  return activities.filter((a) => !linkedIds.has(a.id));
}

type CoachMonthCalendarProps = {
  athleteId: number;
  refreshKey?: number;
  onCalendarChanged?: () => void;
};

export function CoachMonthCalendar({
  athleteId,
  refreshKey = 0,
  onCalendarChanged,
}: CoachMonthCalendarProps) {
  const navigate = useNavigate();
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth());
  const [workouts, setWorkouts] = useState<Workout[]>([]);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [selectedWorkout, setSelectedWorkout] = useState<Workout | null>(null);

  useEffect(() => {
    setLoading(true);
    const { start, end } = monthBounds(year, month);
    Promise.all([
      getAthleteCalendar(athleteId, start, end),
      listAthleteActivities(athleteId, start, end),
    ]).then(([workoutResult, activityResult]) => {
      if (!workoutResult.success) {
        setError(workoutResult.error ?? "Failed to load calendar");
        setWorkouts([]);
      } else {
        setError(null);
        setWorkouts(workoutResult.workouts);
      }
      if (activityResult.success && activityResult.activities) {
        setActivities(activityResult.activities);
      } else {
        setActivities([]);
      }
      setLoading(false);
    });
  }, [athleteId, year, month, refreshKey]);

  const workoutsByDate = useMemo(() => groupByDate(workouts, "scheduled_date"), [workouts]);
  const activitiesByDate = useMemo(() => groupByDate(activities, "date"), [activities]);
  const grid = useMemo(() => buildMonthGrid(year, month), [year, month]);

  const selectedWorkouts = selectedDate ? (workoutsByDate.get(selectedDate) ?? []) : [];
  const selectedActivities = selectedDate
    ? unlinkedActivitiesForDay(selectedWorkouts, activitiesByDate.get(selectedDate) ?? [])
    : [];

  const hasAnyEvents = workouts.length > 0 || activities.length > 0;

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
    setSelectedWorkout(null);
    onCalendarChanged?.();
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

      {!loading && !error && !hasAnyEvents && (
        <p className="muted">No planned workouts or completed activities this month yet.</p>
      )}

      <div className="calendar-weekdays">
        {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => (
          <span key={day}>{day}</span>
        ))}
      </div>

      <div className="calendar-grid">
        {grid.map((iso, index) => {
          if (!iso) return <div key={`empty-${index}`} className="calendar-cell empty" />;
          const dayWorkouts = workoutsByDate.get(iso) ?? [];
          const dayActivities = unlinkedActivitiesForDay(
            dayWorkouts,
            activitiesByDate.get(iso) ?? [],
          );
          const hasEvents = dayWorkouts.length > 0 || dayActivities.length > 0;
          const dayNum = Number(iso.split("-")[2]);
          return (
            <button
              key={iso}
              type="button"
              className={`calendar-cell ${hasEvents ? "has-workout" : ""} ${
                selectedDate === iso ? "selected" : ""
              }`}
              onClick={() => setSelectedDate(iso)}
            >
              <span className="calendar-day">{dayNum}</span>
              {hasEvents && (
                <CalendarDayEvents
                  workouts={dayWorkouts}
                  activities={dayActivities}
                  onWorkoutClick={(id) => {
                    const workout = dayWorkouts.find((w) => w.id === id);
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
          <div className="row-between">
            <h4>{selectedDate}</h4>
            <Link to={`/planning/workout/new?athleteId=${athleteId}&date=${selectedDate}`}>
              <button type="button" className="secondary">
                Schedule workout
              </button>
            </Link>
          </div>
          {selectedWorkouts.length > 0 && (
            <div className="stack">
              <h4>Planned workouts</h4>
              {selectedWorkouts.map((workout) => (
                <WorkoutCard
                  key={workout.id}
                  workout={workout}
                  compact
                  onSelect={() => setSelectedWorkout(workout)}
                />
              ))}
            </div>
          )}
          {selectedActivities.length > 0 && (
            <div className="stack">
              <h4>Completed activities</h4>
              {selectedActivities.map((activity) => (
                <ActivityCard key={activity.id} activity={activity} />
              ))}
            </div>
          )}
          {selectedWorkouts.length === 0 && selectedActivities.length === 0 && (
            <p className="muted">Nothing scheduled or completed on this day.</p>
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
                  onEdit: () => navigate(`/planning/workout/${selectedWorkout.id}`),
                  onDelete: () => handleDelete(selectedWorkout),
                }
              : undefined
          }
        />
      )}
    </div>
  );
}
