import { useEffect, useMemo, useState } from "react";
import { listActivities, type Activity } from "../../activities/api";
import { getCalendar, type Workout } from "../../training/api";
import { formatMonthYear, monthBounds, toDateKey, toIsoDate } from "../../shared/dates";
import { ActivityCard } from "../activities/ActivityCard";
import { CalendarDayEvents } from "./CalendarDayEvents";
import { WorkoutCard } from "./WorkoutCard";

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

export function MonthCalendar() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth());
  const [workouts, setWorkouts] = useState<Workout[]>([]);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    const { start, end } = monthBounds(year, month);
    Promise.all([getCalendar(start, end), listActivities(start, end)]).then(
      ([workoutResult, activityResult]) => {
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
      },
    );
  }, [year, month]);

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

  return (
    <div className="stack">
      <div className="row-between">
        <h2>Training calendar</h2>
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

      <div className="calendar-legend muted">
        <span>
          <span className="calendar-event-chip chip-workout status-scheduled legend-chip">Planned</span>
        </span>
        <span>
          <span className="calendar-event-chip chip-workout status-completed legend-chip">Done</span>
        </span>
        <span>
          <span className="calendar-event-chip chip-activity legend-chip">Activity</span>
        </span>
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
                <CalendarDayEvents workouts={dayWorkouts} activities={dayActivities} />
              )}
            </button>
          );
        })}
      </div>

      {selectedDate && (
        <div className="card stack">
          <h3>{selectedDate}</h3>
          {selectedWorkouts.length > 0 && (
            <div className="stack">
              <h4>Planned workouts</h4>
              {selectedWorkouts.map((workout) => (
                <WorkoutCard key={workout.id} workout={workout} />
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
    </div>
  );
}
