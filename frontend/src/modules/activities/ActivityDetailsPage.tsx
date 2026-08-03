import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getActivity, type Activity } from "./api";
import { formatDistance, formatDuration } from "./format";
import { Chip, PageFrame, SectionBox, SectionRow } from "../shared/PageChrome";
import { addDaysIso, todayIso, toDateKey } from "../shared/dates";
import { getCalendar, type Workout } from "../training/api";
import { formatWorkoutPreview } from "../workout/format";
import { isRepeatBlock, type WorkoutStepItem } from "../workout/types";

function flattenStepLabels(steps: WorkoutStepItem[] | null | undefined, sportCode: string | null) {
  if (!steps?.length) return [] as string[];
  const labels: string[] = [];
  for (const item of steps) {
    if (isRepeatBlock(item)) {
      labels.push(`${item.repeatCount}× block`);
      for (const step of item.steps) {
        labels.push(...formatWorkoutPreview([step], sportCode, true));
      }
    } else {
      labels.push(...formatWorkoutPreview([item], sportCode, true));
    }
  }
  return labels;
}

export function ActivityDetailsPage() {
  const { activityId } = useParams<{ activityId: string }>();
  const id = Number(activityId);

  const [activity, setActivity] = useState<Activity | null>(null);
  const [linkedWorkout, setLinkedWorkout] = useState<Workout | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!Number.isFinite(id)) {
      setError("Invalid activity id");
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    getActivity(id).then(async (result) => {
      if (cancelled) return;
      if (!result.success || !result.activity) {
        setError(result.error ?? "Failed to load activity");
        setLoading(false);
        return;
      }
      setActivity(result.activity);

      const end = todayIso();
      const start = addDaysIso(end, -45);
      const calendar = await getCalendar(start, end);
      if (!cancelled && calendar.success) {
        const match =
          calendar.workouts.find((w) => w.activity_id === result.activity!.id) ?? null;
        setLinkedWorkout(match);
      }
      setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, [id]);

  const plannedLabels = useMemo(
    () => flattenStepLabels(linkedWorkout?.steps, linkedWorkout?.sport_code ?? null),
    [linkedWorkout],
  );

  if (loading) return <p className="muted">Loading activity…</p>;
  if (error) return <p className="error">{error}</p>;
  if (!activity) return <p className="muted">Activity not found.</p>;

  const sportLabel =
    activity.activity_type_code ?? activity.sport_code ?? linkedWorkout?.sport_name ?? "Activity";

  return (
    <PageFrame title={`Activity · ${activity.id}`} question="Was this workout executed well?">
      <SectionBox label="Execution Verdict" note="summary at a glance">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <div>
            <div className="text-lg font-semibold text-slate-900">
              {activity.name}
              {linkedWorkout ? " · linked plan" : ""}
            </div>
            <div className="text-sm text-slate-500">
              {[
                sportLabel,
                formatDuration(activity.total_hours),
                toDateKey(activity.date),
                linkedWorkout ? `vs ${linkedWorkout.title}` : null,
              ]
                .filter(Boolean)
                .join(" · ")}
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Chip>{activity.source}</Chip>
            <Link to="/activities" className="button-link">
              All activities
            </Link>
            <Link to="/today" className="button-link">
              Today
            </Link>
          </div>
        </div>
      </SectionBox>

      <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_320px]">
        <div className="grid gap-3">
          <SectionBox label="Planned vs Actual" note="steps vs recorded summary">
            {linkedWorkout ? (
              <>
                <div className="mb-1 text-[11px] text-slate-400">Planned</div>
                <div className="mb-3 flex flex-wrap gap-1">
                  {plannedLabels.length > 0 ? (
                    plannedLabels.map((label) => <Chip key={label}>{label}</Chip>)
                  ) : (
                    <span className="text-sm text-slate-500">No structured steps</span>
                  )}
                </div>
                <div className="mb-1 text-[11px] text-slate-400">Actual</div>
                <div className="flex flex-wrap gap-1">
                  <Chip>{formatDistance(activity.total_distance_km)}</Chip>
                  <Chip>{formatDuration(activity.total_hours)}</Chip>
                  <Chip>{sportLabel}</Chip>
                  {activity.total_sessions != null && (
                    <Chip>{activity.total_sessions} sessions</Chip>
                  )}
                </div>
              </>
            ) : (
              <p className="text-sm text-slate-500">
                No linked workout plan for this activity.
              </p>
            )}
          </SectionBox>

          <SectionBox label="Charts · Pace / HR / Power" note="streams not available yet">
            <div className="grid gap-2">
              <div className="flex h-16 items-center justify-center rounded border border-dashed border-slate-200 bg-slate-50 text-xs text-slate-400">
                Pace chart placeholder
              </div>
              <div className="flex h-16 items-center justify-center rounded border border-dashed border-slate-200 bg-slate-50 text-xs text-slate-400">
                Heart rate chart placeholder
              </div>
              <div className="flex h-16 items-center justify-center rounded border border-dashed border-slate-200 bg-slate-50 text-xs text-slate-400">
                Power chart placeholder
              </div>
            </div>
          </SectionBox>

          <SectionRow cols={2}>
            <SectionBox label="Laps" note="placeholder">
              <p className="text-sm text-slate-500">
                {activity.total_sessions != null
                  ? `${activity.total_sessions} session(s) recorded — lap breakdown coming soon.`
                  : "Lap data not available yet."}
              </p>
            </SectionBox>
            <SectionBox label="Time in Zones" note="placeholder">
              <p className="text-sm text-slate-500">Zone distribution coming soon.</p>
            </SectionBox>
          </SectionRow>
        </div>

        <div className="grid gap-3">
          <SectionBox label="Summary" note="key stats">
            <div className="grid grid-cols-2 gap-2">
              <Chip>Dist {formatDistance(activity.total_distance_km)}</Chip>
              <Chip>Time {formatDuration(activity.total_hours)}</Chip>
              <Chip>Sport {sportLabel}</Chip>
              <Chip>Source {activity.source}</Chip>
              {activity.strava_activity_id != null && (
                <Chip className="col-span-2">Strava {activity.strava_activity_id}</Chip>
              )}
            </div>
          </SectionBox>

          <SectionBox label="Insights" note="placeholder">
            <ul className="divide-y divide-slate-100 text-sm text-slate-600">
              <li className="py-1.5">Algorithmic and AI insights will appear here.</li>
            </ul>
          </SectionBox>

          <SectionBox label="Notes" note="placeholder">
            <p className="text-sm text-slate-500">Athlete ↔ coach notes coming soon.</p>
            {linkedWorkout?.notes && (
              <p className="mt-2 rounded border border-slate-200 bg-slate-50 p-2 text-sm text-slate-700">
                Workout note: {linkedWorkout.notes}
              </p>
            )}
          </SectionBox>
        </div>
      </div>
    </PageFrame>
  );
}
