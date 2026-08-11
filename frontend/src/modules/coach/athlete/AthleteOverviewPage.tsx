import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getAthleteTodayEntry } from "../../recovery/api";
import { Chip, MetricBar, SectionBox, SectionRow } from "../../shared/PageChrome";
import { addDaysIso, formatDate, todayIso } from "../../shared/dates";
import { getAthleteCalendar, type Workout } from "../../training/api";
import { ReadinessBadge } from "../../athlete/recovery/ReadinessBadge";
import { useAthleteWorkspace } from "./AthleteWorkspaceLayout";
import { mockMesocycle } from "./mockAthleteContext";

const WORKSPACES = [
  { to: "plan", label: "Plan", hint: "What's coming?" },
  { to: "activities", label: "Activities", hint: "Was it executed well?" },
  { to: "performance", label: "Performance", hint: "Are they improving?" },
  { to: "recovery", label: "Recovery", hint: "Ready to train?" },
] as const;

export function AthleteOverviewPage() {
  const { athleteId, detail } = useAthleteWorkspace();
  const { athlete } = detail;
  const meso = mockMesocycle(athleteId);
  const today = todayIso();

  const [readiness, setReadiness] = useState<number | null>(null);
  const [nextSession, setNextSession] = useState<Workout | null>(null);
  const [loadingSnap, setLoadingSnap] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoadingSnap(true);
    Promise.all([
      getAthleteTodayEntry(athleteId),
      getAthleteCalendar(athleteId, today, addDaysIso(today, 7)),
    ]).then(([recoveryResult, calendarResult]) => {
      if (cancelled) return;
      const entry =
        recoveryResult.success && recoveryResult.entry ? recoveryResult.entry : null;
      setReadiness(entry?.readiness_score ?? null);
      const workouts = calendarResult.success ? calendarResult.workouts : [];
      const upcoming = workouts
        .filter((w) => w.status === "scheduled" && w.scheduled_date >= today)
        .sort((a, b) => a.scheduled_date.localeCompare(b.scheduled_date));
      setNextSession(upcoming[0] ?? null);
      setLoadingSnap(false);
    });
    return () => {
      cancelled = true;
    };
  }, [athleteId, today]);

  return (
    <div className="grid gap-3">
      <SectionBox label="Snapshot" note="Current block, readiness, next session">
        <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="text-base font-semibold text-slate-900">{athlete.name}</div>
            <p className="text-xs text-slate-500">
              @{athlete.username} · {athlete.email}
            </p>
            {detail.coaching_since ? (
              <p className="mt-1 text-[11px] text-slate-400">
                Coaching since {formatDate(detail.coaching_since.slice(0, 10))}
              </p>
            ) : null}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Chip>
              {detail.upcoming_workouts_count} upcoming
              <span className="ml-1 text-slate-400">· 7d</span>
            </Chip>
            <Link
              to={`/planning/workout/new?athleteId=${athlete.id}`}
              className="button-link"
            >
              Schedule workout
            </Link>
          </div>
        </div>

        {loadingSnap ? (
          <p className="text-sm text-slate-500">Loading snapshot…</p>
        ) : (
          <SectionRow cols={3}>
            <div className="rounded border border-slate-100 bg-slate-50 p-2">
              <div className="mb-1 flex items-center justify-between gap-2">
                <div className="text-[11px] uppercase text-slate-400">Block</div>
                <Chip className="border-amber-200 bg-amber-50 text-amber-700">Demo</Chip>
              </div>
              <div className="text-sm font-medium text-slate-800">{meso.subtitle}</div>
              <div className="mt-1 text-xs text-slate-500">{meso.goal}</div>
              <div className="mt-2">
                <MetricBar label="Prog" value={meso.progressPct} />
              </div>
            </div>
            <div className="rounded border border-slate-100 bg-slate-50 p-2">
              <div className="mb-1 text-[11px] uppercase text-slate-400">Readiness</div>
              <div className="flex items-center gap-2">
                <ReadinessBadge score={readiness} />
                <span className="text-sm text-slate-700">{readiness ?? "—"}</span>
              </div>
            </div>
            <div className="rounded border border-slate-100 bg-slate-50 p-2">
              <div className="mb-1 text-[11px] uppercase text-slate-400">Next session</div>
              {nextSession ? (
                <>
                  <div className="text-sm font-medium text-slate-800">{nextSession.title}</div>
                  <div className="mt-0.5 text-xs text-slate-500">
                    {formatDate(nextSession.scheduled_date)}
                    {nextSession.sport_name ? ` · ${nextSession.sport_name}` : ""}
                  </div>
                  <Link
                    to={`/planning/workout/${nextSession.id}`}
                    className="mt-1 inline-block text-xs text-slate-700 hover:underline"
                  >
                    Open workout →
                  </Link>
                </>
              ) : (
                <p className="text-sm text-slate-500">No session scheduled in the next 7 days.</p>
              )}
            </div>
          </SectionRow>
        )}
      </SectionBox>

      <SectionBox label="Shared workspaces" note="Open a workspace scoped to this athlete">
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {WORKSPACES.map((w) => (
            <Link
              key={w.to}
              to={w.to}
              className="rounded-md border border-slate-200 p-3 text-sm hover:bg-slate-50"
            >
              <div className="font-medium text-slate-900">{w.label}</div>
              <div className="mt-0.5 text-[11px] text-slate-500">{w.hint}</div>
            </Link>
          ))}
        </div>
      </SectionBox>
    </div>
  );
}
