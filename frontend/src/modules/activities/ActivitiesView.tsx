import { useEffect, useState } from "react";
import { Bike, CalendarDays, Dumbbell, Footprints, List, Waves } from "lucide-react";
import { listActivities, listAthleteActivities, type Activity } from "../activities/api";
import { type SportFilterId } from "../activities/sportFilter";
import { MonthCalendar } from "../calendar/MonthCalendar";
import {
  activityListRangeBounds,
  type ActivityListRangeId,
} from "../shared/dates";
import { cn } from "@/lib/utils";
import { ActivityList } from "../athlete/activities/ActivityList";

const SPORT_OPTIONS: {
  id: SportFilterId;
  label: string;
  Icon: typeof Footprints;
}[] = [
  { id: "run", label: "Run", Icon: Footprints },
  { id: "bike", label: "Bike", Icon: Bike },
  { id: "swim", label: "Swim", Icon: Waves },
  { id: "other", label: "Other", Icon: Dumbbell },
];

function chipClass(active: boolean, size: "view" | "filter" = "filter") {
  return cn(
    "activities-chip",
    size === "view" ? "activities-chip-view" : "activities-chip-filter",
    active && "activities-chip-active",
  );
}

export type ActivitiesViewScope =
  | { type: "self" }
  | { type: "athlete"; athleteId: number };

export type ActivitiesViewProps = {
  scope: ActivitiesViewScope;
  heading?: string;
  subheading?: string;
  /** Coach planning controls on athlete-scoped calendar. */
  coachPlanning?: boolean;
  /** Skip athlete-only empty-state hints (e.g. Strava). */
  coachMode?: boolean;
};

/** Calendar-first + list activities workspace (Evolve ActivitiesView). */
export function ActivitiesView({
  scope,
  heading,
  subheading,
  coachPlanning = false,
  coachMode = false,
}: ActivitiesViewProps) {
  const [view, setView] = useState<"calendar" | "list">("calendar");
  const [sportFilter, setSportFilter] = useState<SportFilterId[]>([]);
  const [rangeId, setRangeId] = useState<ActivityListRangeId>("7d");
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [calendarRefreshKey, setCalendarRefreshKey] = useState(0);

  const athleteId = scope.type === "athlete" ? scope.athleteId : null;

  useEffect(() => {
    if (view !== "list") return;

    let cancelled = false;
    setLoading(true);
    setError(null);
    const { start, end } = activityListRangeBounds(rangeId);

    const request =
      athleteId != null
        ? listAthleteActivities(athleteId, start, end)
        : listActivities(start, end);

    request.then((result) => {
      if (cancelled) return;
      if (!result.success || !result.activities) {
        setError(result.error ?? "Failed to load activities");
        setActivities([]);
      } else {
        setActivities(result.activities);
      }
      setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, [view, rangeId, athleteId]);

  function toggleSport(id: SportFilterId) {
    setSportFilter((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id],
    );
  }

  return (
    <div className="stack activities-page">
      {(heading || subheading) && (
        <div className="mb-1">
          {heading ? (
            <h2 className="text-base font-semibold tracking-tight text-slate-900">{heading}</h2>
          ) : null}
          {subheading ? <p className="text-xs text-slate-500">{subheading}</p> : null}
        </div>
      )}

      <div className="flex items-center justify-end gap-2">
        <button
          type="button"
          className={chipClass(view === "calendar", "view")}
          onClick={() => setView("calendar")}
          aria-pressed={view === "calendar"}
        >
          <CalendarDays className="activities-chip-icon" aria-hidden />
          Calendar
        </button>
        <button
          type="button"
          className={chipClass(view === "list", "view")}
          onClick={() => setView("list")}
          aria-pressed={view === "list"}
        >
          <List className="activities-chip-icon" aria-hidden />
          List
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[11px] uppercase tracking-wider text-slate-400">Sport</span>
        {SPORT_OPTIONS.map(({ id, label, Icon }) => (
          <button
            key={id}
            type="button"
            className={chipClass(sportFilter.includes(id), "filter")}
            onClick={() => toggleSport(id)}
            aria-pressed={sportFilter.includes(id)}
          >
            <Icon className="activities-chip-icon" aria-hidden />
            {label}
          </button>
        ))}
        {sportFilter.length > 0 ? (
          <button
            type="button"
            className="activities-chip activities-chip-ghost"
            onClick={() => setSportFilter([])}
          >
            Clear
          </button>
        ) : (
          <span className="text-xs text-slate-400">All sports</span>
        )}
      </div>

      {view === "calendar" ? (
        <MonthCalendar
          scope={scope}
          showWorkouts
          showActivities
          sportFilter={sportFilter}
          coachPlanning={
            coachPlanning && athleteId != null
              ? {
                  enabled: true,
                  refreshKey: calendarRefreshKey,
                  onCalendarChanged: () => setCalendarRefreshKey((k) => k + 1),
                }
              : undefined
          }
        />
      ) : (
        <ActivityList
          activities={activities}
          sportFilter={sportFilter}
          rangeId={rangeId}
          onRangeChange={setRangeId}
          loading={loading}
          error={error}
          coachMode={coachMode}
        />
      )}
    </div>
  );
}
