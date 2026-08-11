import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Chip, MetricBar, SectionBox } from "../../shared/PageChrome";
import { formatDate, todayIso, weekBounds } from "../../shared/dates";
import { getAthleteCalendar, type Workout } from "../../training/api";
import { useAthleteWorkspace } from "./AthleteWorkspaceLayout";
import { mockMesocycle } from "./mockAthleteContext";

export function AthletePlanPage() {
  const { athleteId, detail } = useAthleteWorkspace();
  const meso = mockMesocycle(athleteId);
  const today = todayIso();
  const week = weekBounds(today);

  const [workouts, setWorkouts] = useState<Workout[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getAthleteCalendar(athleteId, week.start, week.end).then((result) => {
      if (cancelled) return;
      if (!result.success) {
        setError(result.error ?? "Failed to load week");
        setWorkouts([]);
      } else {
        setError(null);
        setWorkouts(
          [...(result.workouts ?? [])].sort((a, b) =>
            a.scheduled_date.localeCompare(b.scheduled_date),
          ),
        );
      }
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [athleteId, week.start, week.end]);

  return (
    <div className="grid gap-3">
      <SectionBox label="Current Mesocycle" note="Where are they in the plan?">
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <Chip className="border-amber-200 bg-amber-50 text-amber-700">Demo</Chip>
          <span className="text-sm font-medium text-slate-900">{meso.name}</span>
        </div>
        <p className="mb-2 text-sm text-slate-600">
          Week {meso.week} of {meso.weeksTotal} · Goal: {meso.goal}
        </p>
        <MetricBar label="Prog" value={meso.progressPct} />
        <p className="mt-2 text-[11px] text-slate-400">
          Mesocycle data is not on the backend yet — showing demo progress.
        </p>
      </SectionBox>

      <SectionBox label="This Week" note="Upcoming sessions">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <p className="text-xs text-slate-500">
            {formatDate(week.start)} – {formatDate(week.end)}
          </p>
          <Link
            to={`/planning/workout/new?athleteId=${detail.athlete.id}`}
            className="button-link"
          >
            Schedule workout
          </Link>
        </div>
        {loading && <p className="text-sm text-slate-500">Loading week…</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
        {!loading && !error && workouts.length === 0 && (
          <p className="text-sm text-slate-500">No sessions planned this week.</p>
        )}
        {!loading && !error && workouts.length > 0 && (
          <ul className="divide-y divide-slate-100 text-sm">
            {workouts.map((w) => (
              <li key={w.id} className="flex items-center justify-between gap-3 py-2">
                <div>
                  <div className="font-medium text-slate-900">{w.title}</div>
                  <div className="text-xs text-slate-500">
                    {formatDate(w.scheduled_date)}
                    {w.sport_name ? ` · ${w.sport_name}` : ""}
                    {w.workout_type ? ` · ${w.workout_type}` : ""}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Chip>{w.status}</Chip>
                  <Link
                    to={`/planning/workout/${w.id}`}
                    className="text-xs text-slate-700 hover:underline"
                  >
                    Open →
                  </Link>
                </div>
              </li>
            ))}
          </ul>
        )}
      </SectionBox>
    </div>
  );
}
