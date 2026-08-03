import { useEffect, useState } from "react";
import { Bike, CalendarDays, Dumbbell, Footprints, List, Waves } from "lucide-react";
import { listActivities, type Activity } from "../activities/api";
import { type SportFilterId } from "../activities/sportFilter";
import { MonthCalendar } from "../calendar/MonthCalendar";
import {
  activityListRangeBounds,
  type ActivityListRangeId,
} from "../shared/dates";
import { cn } from "@/lib/utils";
import { ActivityList } from "./activities/ActivityList";
import { SettingsTab } from "./tabs/SettingsTab";

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

/** Athlete activities workspace (calendar-first + list). */
export function ActivitiesPage() {
  const [view, setView] = useState<"calendar" | "list">("calendar");
  const [sportFilter, setSportFilter] = useState<SportFilterId[]>([]);
  const [rangeId, setRangeId] = useState<ActivityListRangeId>("7d");
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (view !== "list") return;

    let cancelled = false;
    setLoading(true);
    setError(null);
    const { start, end } = activityListRangeBounds(rangeId);

    listActivities(start, end).then((result) => {
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
  }, [view, rangeId]);

  function toggleSport(id: SportFilterId) {
    setSportFilter((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id],
    );
  }

  return (
    <div className="stack activities-page">
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
          scope={{ type: "self" }}
          showWorkouts={false}
          showActivities
          sportFilter={sportFilter}
        />
      ) : (
        <ActivityList
          activities={activities}
          sportFilter={sportFilter}
          rangeId={rangeId}
          onRangeChange={setRangeId}
          loading={loading}
          error={error}
        />
      )}
    </div>
  );
}

/** Athlete settings (Strava + profile link). */
export function AthleteSettingsPage() {
  return <SettingsTab />;
}
