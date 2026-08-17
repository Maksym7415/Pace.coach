import { useEffect, useMemo, useRef, useState, type ChangeEvent } from "react";
import { Link } from "react-router-dom";
import { listActivities, importFitFile, type Activity } from "../../activities/api";
import { formatActivityMeta, formatDistance, formatDuration } from "../../activities/format";
import { useAuth } from "../../auth/AuthContext";
import { getTodayEntry, type RecoveryEntry } from "../../recovery/api";
import { Chip, MetricBar, PageFrame, SectionBox, SectionRow } from "../../shared/PageChrome";
import { addDaysIso, todayIso, toDateKey, weekBounds } from "../../shared/dates";
import { getCalendar, completeWorkout, skipWorkout, type Workout } from "../../training/api";
import { formatWorkoutPreview } from "../../workout/format";
import { isRepeatBlock, type WorkoutStepItem } from "../../workout/types";
import { WorkoutDetailModal } from "../../workout/WorkoutDetailModal";
import { PendingInvitationsBanner } from "../PendingInvitationsBanner";
import { RecoveryForm } from "../recovery/RecoveryForm";
import { ReadinessBadge } from "../recovery/ReadinessBadge";

function stepChips(steps: WorkoutStepItem[] | null | undefined, sportCode: string | null): string[] {
  if (!steps?.length) return [];
  const chips: string[] = [];
  for (const item of steps.slice(0, 8)) {
    if (isRepeatBlock(item)) {
      chips.push(`${item.repeatCount}×`);
    } else {
      const preview = formatWorkoutPreview([item], sportCode, true)[0];
      chips.push(preview?.split(" · ")[0] ?? item.type);
    }
  }
  if (steps.length > 8) chips.push("…");
  return chips;
}

export function AthleteTodayPage() {
  const { user } = useAuth();
  const today = todayIso();
  const tomorrow = addDaysIso(today, 1);
  const week = useMemo(() => weekBounds(today), [today]);

  const [recovery, setRecovery] = useState<RecoveryEntry | null>(null);
  const [editingCheckIn, setEditingCheckIn] = useState(false);
  const [todayWorkouts, setTodayWorkouts] = useState<Workout[]>([]);
  const [weekWorkouts, setWeekWorkouts] = useState<Workout[]>([]);
  const [recentActivity, setRecentActivity] = useState<Activity | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedWorkout, setSelectedWorkout] = useState<Workout | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    Promise.all([
      getTodayEntry(),
      getCalendar(today, today),
      getCalendar(week.start, week.end),
      listActivities(addDaysIso(today, -14), today),
    ]).then(([recoveryResult, todayResult, weekResult, activitiesResult]) => {
      if (cancelled) return;

      if (recoveryResult.entry) setRecovery(recoveryResult.entry);
      if (!todayResult.success) {
        setError(todayResult.error ?? "Failed to load today's workouts");
      } else {
        setTodayWorkouts(todayResult.workouts);
      }
      if (weekResult.success) setWeekWorkouts(weekResult.workouts);
      if (activitiesResult.success && activitiesResult.activities?.length) {
        const sorted = [...activitiesResult.activities].sort((a, b) =>
          toDateKey(b.date).localeCompare(toDateKey(a.date)),
        );
        setRecentActivity(sorted[0] ?? null);
      }
      setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, [today, week.start, week.end]);

  async function refreshWorkouts() {
    const [todayResult, weekResult] = await Promise.all([
      getCalendar(today, today),
      getCalendar(week.start, week.end),
    ]);
    if (todayResult.success) setTodayWorkouts(todayResult.workouts);
    if (weekResult.success) setWeekWorkouts(weekResult.workouts);
  }

  const primaryWorkout = todayWorkouts[0] ?? null;
  const workoutsByDay = useMemo(() => {
    const map = new Map<string, Workout[]>();
    for (const w of weekWorkouts) {
      const key = toDateKey(w.scheduled_date);
      const list = map.get(key) ?? [];
      list.push(w);
      map.set(key, list);
    }
    return map;
  }, [weekWorkouts]);

  const previousFromWorkout = useMemo(() => {
    const completed = weekWorkouts
      .filter((w) => w.status === "completed" && toDateKey(w.scheduled_date) < today)
      .sort((a, b) => toDateKey(b.scheduled_date).localeCompare(toDateKey(a.scheduled_date)));
    return completed[0] ?? null;
  }, [weekWorkouts, today]);

  async function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !user) return;
    if (!file.name.toLowerCase().endsWith(".fit")) {
      setUploadMessage("Please select a .fit file");
      return;
    }
    setUploading(true);
    setUploadMessage(null);
    try {
      const result = await importFitFile(user.id, file);
      setUploadMessage(
        result.success
          ? "Activity uploaded — processing in background."
          : (result.error ?? "Failed to upload activity"),
      );
    } catch {
      setUploadMessage("Failed to upload activity");
    } finally {
      setUploading(false);
    }
  }

  const dayLabels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  return (
    <div className="space-y-3">
      <PendingInvitationsBanner />
      <PageFrame title="Athlete · Today" question="What should I do today, and am I ready?">
        {loading && <p className="text-sm text-slate-500">Loading today…</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}

        <SectionRow cols={3}>
          {loading ? (
            <SectionBox label="Readiness" note="loading">
              <p className="text-sm text-slate-500">Loading…</p>
            </SectionBox>
          ) : !recovery || editingCheckIn ? (
            <SectionBox
              label="Readiness · Check-in"
              note={recovery ? "editing today's check-in" : "no data yet today"}
            >
              <RecoveryForm
                variant="check-in"
                initialEntry={recovery}
                onCancel={recovery ? () => setEditingCheckIn(false) : undefined}
                onSaved={(entry) => {
                  setRecovery(entry);
                  setEditingCheckIn(false);
                }}
              />
            </SectionBox>
          ) : (
            <SectionBox label="Readiness" note="manual check-in">
              <div className="mb-2 flex items-baseline justify-between gap-2">
                <div className="text-2xl font-semibold text-slate-900">
                  {recovery.readiness_score ?? "—"}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-slate-400">manual</span>
                  <ReadinessBadge score={recovery.readiness_score ?? null} />
                </div>
              </div>
              <div className="space-y-1.5">
                <MetricBar
                  label="Energy"
                  value={
                    recovery.fatigue != null ? (11 - recovery.fatigue) * 10 : null
                  }
                />
                <MetricBar
                  label="Sleep"
                  value={
                    recovery.sleep_quality != null
                      ? recovery.sleep_quality * 10
                      : recovery.sleep_hours != null
                        ? Math.min(100, recovery.sleep_hours * 12.5)
                        : null
                  }
                />
                <MetricBar
                  label="Soreness"
                  value={recovery.soreness != null ? recovery.soreness * 10 : null}
                />
                <MetricBar label="HRV (opt.)" value={recovery.hrv_ms ?? null} max={120} />
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <button type="button" onClick={() => setEditingCheckIn(true)}>
                  Edit today's check-in
                </button>
              </div>
            </SectionBox>
          )}

          <SectionBox label="Today's Session" note="primary focus" className="md:col-span-2">
            {primaryWorkout ? (
              <>
                <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
                  <div>
                    <div className="text-sm font-semibold text-slate-900">{primaryWorkout.title}</div>
                    <div className="text-xs text-slate-500">
                      {[
                        primaryWorkout.sport_name ?? primaryWorkout.sport_code,
                        primaryWorkout.duration_min != null
                          ? `${primaryWorkout.duration_min} min`
                          : null,
                        primaryWorkout.workout_type,
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </div>
                  </div>
                  <Chip>{primaryWorkout.sport_code ?? "sport"}</Chip>
                </div>
                <div className="mb-2 flex flex-wrap gap-1">
                  {stepChips(primaryWorkout.steps, primaryWorkout.sport_code).map((chip) => (
                    <Chip key={chip}>{chip}</Chip>
                  ))}
                </div>
                {todayWorkouts.length > 1 && (
                  <p className="mb-2 text-[11px] text-slate-500">
                    +{todayWorkouts.length - 1} more session
                    {todayWorkouts.length > 2 ? "s" : ""} today
                  </p>
                )}
                <div className="flex flex-wrap gap-2">
                  <button type="button" onClick={() => setSelectedWorkout(primaryWorkout)}>
                    Open workout
                  </button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".fit"
                    hidden
                    onChange={handleFileChange}
                  />
                  <button
                    type="button"
                    className="secondary"
                    disabled={uploading || !user}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    {uploading ? "Uploading…" : "Upload activity"}
                  </button>
                  <Link to="/activities" className="button-link">
                    Activities
                  </Link>
                </div>
                {uploadMessage && <p className="mt-2 text-xs text-slate-500">{uploadMessage}</p>}
              </>
            ) : (
              <div className="space-y-2">
                <p className="text-sm text-slate-500">No workout planned today.</p>
                <div className="flex flex-wrap gap-2">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".fit"
                    hidden
                    onChange={handleFileChange}
                  />
                  <button
                    type="button"
                    disabled={uploading || !user}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    {uploading ? "Uploading…" : "Upload activity"}
                  </button>
                  <Link to="/activities" className="button-link">
                    Activities
                  </Link>
                </div>
                {uploadMessage && <p className="text-xs text-slate-500">{uploadMessage}</p>}
              </div>
            )}
          </SectionBox>
        </SectionRow>

        <SectionBox label="Previous Workout" note="recent activity or completed session">
          {previousFromWorkout ? (
            <div className="space-y-3">
              <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-slate-100 pb-2">
                <div>
                  <div className="text-sm font-semibold text-slate-900">
                    {previousFromWorkout.title}
                    {previousFromWorkout.sport_name ? ` · ${previousFromWorkout.sport_name}` : ""}
                  </div>
                  <div className="text-xs text-slate-500">
                    {toDateKey(previousFromWorkout.scheduled_date)}
                    {previousFromWorkout.linked_activity
                      ? ` · ${formatActivityMeta(previousFromWorkout.linked_activity)}`
                      : ""}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <div className="text-[10px] uppercase text-slate-400">Status</div>
                    <div className="text-sm font-semibold text-slate-900">
                      {previousFromWorkout.status}
                    </div>
                  </div>
                  {previousFromWorkout.activity_id ? (
                    <Link
                      to={`/activity/${previousFromWorkout.activity_id}`}
                      className="button-link"
                    >
                      Open activity
                    </Link>
                  ) : (
                    <button type="button" className="secondary" onClick={() => setSelectedWorkout(previousFromWorkout)}>
                      Open workout
                    </button>
                  )}
                </div>
              </div>
              <div>
                <div className="mb-1 text-[11px] uppercase text-slate-400">AI insight</div>
                <p className="text-sm text-slate-600">
                  Insights will appear here once analysis is available.
                </p>
              </div>
            </div>
          ) : recentActivity ? (
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <div>
                <div className="text-sm font-semibold text-slate-900">{recentActivity.name}</div>
                <div className="text-xs text-slate-500">
                  {formatDistance(recentActivity.total_distance_km)} ·{" "}
                  {formatDuration(recentActivity.total_hours)} · {toDateKey(recentActivity.date)}
                </div>
              </div>
              <Link to={`/activity/${recentActivity.id}`} className="button-link">
                Open activity
              </Link>
            </div>
          ) : (
            <p className="text-sm text-slate-500">No recent workouts yet.</p>
          )}
        </SectionBox>

        <SectionBox label="This Week" note="calendar strip">
          <div className="grid grid-cols-7 gap-2">
            {week.days.map((day, i) => {
              const isToday = day === today;
              const isTomorrow = day === tomorrow;
              const dayWorkouts = workoutsByDay.get(day) ?? [];
              return (
                <div
                  key={day}
                  className={`rounded border p-2 ${
                    isToday
                      ? "border-slate-700 bg-slate-50"
                      : isTomorrow
                        ? "border-slate-400 bg-slate-50/50"
                        : "border-slate-200"
                  }`}
                >
                  <div className="text-[10px] uppercase text-slate-400">
                    {dayLabels[i]}
                    {isToday ? " · today" : isTomorrow ? " · tomorrow" : ""}
                  </div>
                  <div className="mt-1 min-h-6 text-[11px] text-slate-700">
                    {dayWorkouts.length === 0
                      ? "—"
                      : dayWorkouts.map((w) => w.title).join(", ")}
                  </div>
                  <div className="mt-1 text-[10px] text-slate-400">
                    {dayWorkouts[0]?.status ?? "rest"}
                  </div>
                </div>
              );
            })}
          </div>
        </SectionBox>
      </PageFrame>

      {selectedWorkout && (
        <WorkoutDetailModal
          workout={selectedWorkout}
          onClose={() => {
            setSelectedWorkout(null);
            setActionError(null);
          }}
          athleteActions={{
            onComplete: async () => {
              setActionError(null);
              const result = await completeWorkout(selectedWorkout.id);
              if (!result.success) {
                setActionError(result.error ?? "Failed to mark workout complete");
                return;
              }
              setSelectedWorkout(null);
              await refreshWorkouts();
            },
            onSkip: async () => {
              setActionError(null);
              const result = await skipWorkout(selectedWorkout.id);
              if (!result.success) {
                setActionError(result.error ?? "Failed to skip workout");
                return;
              }
              setSelectedWorkout(null);
              await refreshWorkouts();
            },
          }}
          actionError={actionError}
        />
      )}
    </div>
  );
}
