import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import {
  listActivities,
  listAthleteActivities,
  type Activity,
} from "../activities/api";
import {
  activityMatchesSportFilter,
  type SportFilterId,
} from "../activities/sportFilter";
import { ActivityCard } from "../athlete/activities/ActivityCard";
import { CalendarDayEvents } from "../athlete/calendar/CalendarDayEvents";
import { WorkoutCard } from "../athlete/calendar/WorkoutCard";
import { formatMonthYear, monthBounds, todayIso } from "../shared/dates";
import {
  deleteWorkout,
  getAthleteCalendar,
  getCalendar,
  type Workout,
} from "../training/api";
import { WorkoutDetailModal } from "../workout/WorkoutDetailModal";
import { buildMonthGrid, groupByDate, unlinkedActivitiesForDay } from "./monthGrid";

const MONTH_ABBREV = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

export type MonthCalendarProps = {
  scope: { type: "self" } | { type: "athlete"; athleteId: number };
  showWorkouts: boolean;
  showActivities: boolean;
  sportFilter?: SportFilterId[];
  coachPlanning?: {
    enabled: boolean;
    refreshKey?: number;
    onCalendarChanged?: () => void;
  };
};

export function MonthCalendar({
  scope,
  showWorkouts,
  showActivities,
  sportFilter = [],
  coachPlanning,
}: MonthCalendarProps) {
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
  const [pickerOpen, setPickerOpen] = useState(false);
  const [pickerYear, setPickerYear] = useState(now.getFullYear());
  const pickerRef = useRef<HTMLDivElement>(null);

  const athleteId = scope.type === "athlete" ? scope.athleteId : null;
  const refreshKey = coachPlanning?.refreshKey ?? 0;
  const coachingEnabled = coachPlanning?.enabled === true;
  const today = todayIso();
  /** Coach planning keeps day select + panel; activities-only opens chips directly. */
  const daySelectEnabled = showWorkouts;

  useEffect(() => {
    if (!pickerOpen) return;
    function onPointerDown(event: MouseEvent) {
      if (!pickerRef.current?.contains(event.target as Node)) {
        setPickerOpen(false);
      }
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setPickerOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [pickerOpen]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const { start, end } = monthBounds(year, month);

    const workoutPromise = showWorkouts
      ? scope.type === "athlete"
        ? getAthleteCalendar(scope.athleteId, start, end)
        : getCalendar(start, end)
      : Promise.resolve(null);

    const activityPromise = showActivities
      ? scope.type === "athlete"
        ? listAthleteActivities(scope.athleteId, start, end)
        : listActivities(start, end)
      : Promise.resolve(null);

    Promise.all([workoutPromise, activityPromise]).then(([workoutResult, activityResult]) => {
      if (cancelled) return;

      if (workoutResult) {
        if (!workoutResult.success) {
          setError(workoutResult.error ?? "Failed to load calendar");
          setWorkouts([]);
        } else {
          setError(null);
          setWorkouts(workoutResult.workouts);
        }
      } else {
        setWorkouts([]);
      }

      if (activityResult) {
        if (activityResult.success && activityResult.activities) {
          if (!workoutResult || workoutResult.success) setError(null);
          setActivities(activityResult.activities);
        } else {
          if (!showWorkouts) {
            setError(activityResult.error ?? "Failed to load activities");
          }
          setActivities([]);
        }
      } else {
        setActivities([]);
      }

      if (!workoutResult && !activityResult) {
        setError(null);
      }

      setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, [scope.type, athleteId, year, month, refreshKey, showWorkouts, showActivities]);

  const filteredActivities = useMemo(
    () => activities.filter((a) => activityMatchesSportFilter(a, sportFilter)),
    [activities, sportFilter],
  );

  const workoutsByDate = useMemo(() => groupByDate(workouts, "scheduled_date"), [workouts]);
  const activitiesByDate = useMemo(
    () => groupByDate(filteredActivities, "date"),
    [filteredActivities],
  );
  const grid = useMemo(() => buildMonthGrid(year, month), [year, month]);

  const selectedWorkouts = selectedDate && showWorkouts ? (workoutsByDate.get(selectedDate) ?? []) : [];
  const selectedDayActivities = selectedDate
    ? (activitiesByDate.get(selectedDate) ?? [])
    : [];
  const selectedActivities =
    showWorkouts
      ? unlinkedActivitiesForDay(selectedWorkouts, selectedDayActivities)
      : selectedDayActivities;

  const hasAnyEvents =
    (showWorkouts && workouts.length > 0) || (showActivities && filteredActivities.length > 0);

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
    coachPlanning?.onCalendarChanged?.();
  }

  const emptyMessage =
    showWorkouts && showActivities
      ? "No planned workouts or completed activities this month yet."
      : showWorkouts
        ? "No planned workouts this month yet."
        : "No activities this month yet.";

  return (
    <div className="stack">
      <h3>Training calendar</h3>

      <div className="calendar-month-switcher">
        <button
          type="button"
          className="calendar-nav-icon"
          aria-label="Previous month"
          onClick={() => {
            setPickerOpen(false);
            prevMonth();
          }}
        >
          <ChevronLeft className="calendar-nav-chevron" aria-hidden />
        </button>

        <div className="calendar-month-picker" ref={pickerRef}>
          <button
            type="button"
            className="calendar-month-label"
            aria-haspopup="dialog"
            aria-expanded={pickerOpen}
            onClick={() => {
              setPickerYear(year);
              setPickerOpen((open) => !open);
            }}
          >
            {formatMonthYear(year, month)}
          </button>

          {pickerOpen && (
            <div className="calendar-month-popover" role="dialog" aria-label="Choose month">
              <div className="calendar-month-popover-year">
                <button
                  type="button"
                  className="calendar-nav-icon"
                  aria-label="Previous year"
                  onClick={() => setPickerYear((y) => y - 1)}
                >
                  <ChevronLeft className="calendar-nav-chevron" aria-hidden />
                </button>
                <span className="calendar-month-popover-year-label">{pickerYear}</span>
                <button
                  type="button"
                  className="calendar-nav-icon"
                  aria-label="Next year"
                  onClick={() => setPickerYear((y) => y + 1)}
                >
                  <ChevronRight className="calendar-nav-chevron" aria-hidden />
                </button>
              </div>
              <div className="calendar-month-popover-grid">
                {MONTH_ABBREV.map((label, index) => {
                  const active = pickerYear === year && index === month;
                  return (
                    <button
                      key={label}
                      type="button"
                      className={`calendar-month-popover-month${active ? " active" : ""}`}
                      onClick={() => {
                        setYear(pickerYear);
                        setMonth(index);
                        setPickerOpen(false);
                      }}
                    >
                      {label}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        <button
          type="button"
          className="calendar-nav-icon"
          aria-label="Next month"
          onClick={() => {
            setPickerOpen(false);
            nextMonth();
          }}
        >
          <ChevronRight className="calendar-nav-chevron" aria-hidden />
        </button>
      </div>

      {loading && <p className="muted">Loading calendar…</p>}
      {error && <p className="error">{error}</p>}

      {!loading && !error && !hasAnyEvents && <p className="muted">{emptyMessage}</p>}

      <div className="calendar-weekdays">
        {["M", "T", "W", "T", "F", "S", "S"].map((day, i) => (
          <span key={`${day}-${i}`}>{day}</span>
        ))}
      </div>

      <div className="calendar-grid">
        {grid.map((cell) => {
          const { iso, inMonth } = cell;
          const dayWorkouts =
            inMonth && showWorkouts ? (workoutsByDate.get(iso) ?? []) : [];
          const dayActivitiesRaw =
            inMonth && showActivities ? (activitiesByDate.get(iso) ?? []) : [];
          const dayActivities = showWorkouts
            ? unlinkedActivitiesForDay(dayWorkouts, dayActivitiesRaw)
            : dayActivitiesRaw;
          const hasEvents = dayWorkouts.length > 0 || dayActivities.length > 0;
          const dayNum = Number(iso.split("-")[2]);
          const isToday = iso === today;

          const events = hasEvents ? (
            <CalendarDayEvents
              workouts={dayWorkouts}
              activities={dayActivities}
              onWorkoutClick={
                showWorkouts
                  ? (id) => {
                      const workout = dayWorkouts.find((w) => w.id === id);
                      if (workout) setSelectedWorkout(workout);
                    }
                  : undefined
              }
              onActivityClick={(id) => navigate(`/activity/${id}`)}
            />
          ) : null;

          if (!inMonth) {
            return (
              <div key={iso} className="calendar-cell outside-month" aria-disabled="true">
                <span className="calendar-day">{dayNum}</span>
              </div>
            );
          }

          if (!daySelectEnabled) {
            return (
              <div
                key={iso}
                className={`calendar-cell calendar-cell-static ${hasEvents ? "has-workout" : ""} ${
                  isToday ? "is-today" : ""
                }`}
              >
                <span className="calendar-day">{dayNum}</span>
                {events}
              </div>
            );
          }

          return (
            <button
              key={iso}
              type="button"
              className={`calendar-cell ${hasEvents ? "has-workout" : ""} ${
                selectedDate === iso ? "selected" : ""
              } ${isToday ? "is-today" : ""}`}
              onClick={() => setSelectedDate(iso)}
            >
              <span className="calendar-day">{dayNum}</span>
              {events}
            </button>
          );
        })}
      </div>

      {daySelectEnabled && selectedDate && (
        <div className="card stack">
          <div className="row-between">
            <h4>{selectedDate}</h4>
            {coachingEnabled && athleteId != null && (
              <Link to={`/planning/workout/new?athleteId=${athleteId}&date=${selectedDate}`}>
                <button type="button" className="secondary">
                  Schedule workout
                </button>
              </Link>
            )}
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
          {showActivities && selectedActivities.length > 0 && (
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
            coachingEnabled && selectedWorkout.status === "scheduled"
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
