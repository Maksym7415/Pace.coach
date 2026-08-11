import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getActivity, type Activity } from "./api";
import { formatDistance, formatDuration } from "./format";
import { Chip, PageFrame, SectionBox } from "../shared/PageChrome";
import { toDateKey } from "../shared/dates";
import { getWorkoutExecution, saveAthleteResponses } from "../execution/api";
import { PlannedVsActual } from "../execution/PlannedVsActual";
import {
  allIssuesResponded,
  firstQuestionIndexForStep,
  questionsForExecution,
  type IssueResponse,
} from "../execution/questions";
import type { StepExecution, WorkoutExecution } from "../execution/types";
import {
  WorkoutReviewBanner,
  WorkoutReviewDrawer,
  WorkoutReviewedLine,
} from "../execution/WorkoutReviewDrawer";

export function ActivityDetailsPage() {
  const { activityId } = useParams<{ activityId: string }>();
  const id = Number(activityId);

  const [activity, setActivity] = useState<Activity | null>(null);
  const [execution, setExecution] = useState<WorkoutExecution | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerStartIndex, setDrawerStartIndex] = useState(0);

  useEffect(() => {
    if (!Number.isFinite(id)) {
      setError("Invalid activity id");
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.all([getActivity(id), getWorkoutExecution(id)]).then(([activityResult, execResult]) => {
      if (cancelled) return;
      if (!activityResult.success || !activityResult.activity) {
        setError(activityResult.error ?? "Failed to load activity");
        setLoading(false);
        return;
      }
      setActivity(activityResult.activity);
      if (execResult.success) {
        setExecution(execResult.workout_execution ?? null);
      } else {
        setExecution(null);
      }
      setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, [id]);

  const questions = useMemo(
    () => (execution ? questionsForExecution(execution) : []),
    [execution],
  );
  const reviewed = allIssuesResponded(execution);

  function openReview(startIndex = 0) {
    setDrawerStartIndex(startIndex);
    setDrawerOpen(true);
  }

  function handleSelectStep(step: StepExecution) {
    const idx = firstQuestionIndexForStep(questions, step);
    if (idx >= 0) openReview(idx);
  }

  async function handleReviewComplete(responses: Record<number, IssueResponse>) {
    const payload = Object.entries(responses).map(([issueId, response]) => ({
      issue_id: Number(issueId),
      reason: response.reason ?? null,
      reason_other: response.otherText ?? null,
      notes: response.notes ?? null,
    }));
    const result = await saveAthleteResponses(id, payload);
    if (!result.success || !result.workout_execution) {
      throw new Error(result.error ?? "Failed to save responses");
    }
    setExecution(result.workout_execution);
  }

  if (loading) return <p className="muted">Loading activity…</p>;
  if (error) return <p className="error">{error}</p>;
  if (!activity) return <p className="muted">Activity not found.</p>;

  const sportLabel =
    activity.activity_type_code ??
    activity.sport_code ??
    execution?.workout.sport_code ??
    "Activity";

  const contextLabel = execution
    ? `${execution.workout.title} · ${toDateKey(activity.date)}`
    : toDateKey(activity.date);

  return (
    <PageFrame title={`Activity · ${activity.id}`} question="Was this workout executed well?">
      <SectionBox label="Execution Verdict" note="summary at a glance">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <div>
            <div className="text-lg font-semibold text-slate-900">
              {activity.name}
              {execution ? " · linked plan" : ""}
            </div>
            <div className="text-sm text-slate-500">
              {[
                sportLabel,
                formatDuration(activity.total_hours),
                toDateKey(activity.date),
                execution ? `vs ${execution.workout.title}` : null,
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

      {!reviewed && questions.length > 0 ? (
        <WorkoutReviewBanner count={questions.length} onReview={() => openReview(0)} />
      ) : null}

      <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_320px]">
        <div className="grid gap-3">
          {execution ? (
            <PlannedVsActual execution={execution} onSelectStep={handleSelectStep} />
          ) : (
            <SectionBox label="Planned vs Actual" note="matched workout steps">
              <p className="text-sm text-slate-500">
                No workout execution for this activity yet. Structured FIT imports with a linked
                plan will appear here.
              </p>
            </SectionBox>
          )}

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

          <SectionBox label="Time in Zones" note="placeholder">
            <p className="text-sm text-slate-500">Zone distribution coming soon.</p>
          </SectionBox>
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
            {reviewed && questions.length > 0 ? (
              <div className="mt-2">
                <WorkoutReviewedLine count={questions.length} />
              </div>
            ) : null}
          </SectionBox>

          <SectionBox label="Notes" note="placeholder">
            <p className="text-sm text-slate-500">Athlete ↔ coach notes coming soon.</p>
          </SectionBox>
        </div>
      </div>

      {questions.length > 0 ? (
        <WorkoutReviewDrawer
          questions={questions}
          contextLabel={contextLabel}
          sportCode={execution?.workout.sport_code ?? null}
          startIndex={drawerStartIndex}
          open={drawerOpen}
          onOpenChange={setDrawerOpen}
          onComplete={handleReviewComplete}
        />
      ) : null}
    </PageFrame>
  );
}
