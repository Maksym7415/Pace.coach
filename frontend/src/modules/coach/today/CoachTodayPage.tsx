import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { listAthletes, type CoachAthleteListItem } from "../../coaching/api";
import { getAthleteTodayEntry, type RecoveryEntry } from "../../recovery/api";
import { Chip, PageFrame, SectionBox, SectionRow } from "../../shared/PageChrome";
import { todayIso } from "../../shared/dates";
import { getAthleteCalendar, type Workout } from "../../training/api";
import { ReadinessBadge } from "../../athlete/recovery/ReadinessBadge";

type AthleteDayData = {
  athleteId: number;
  recovery: RecoveryEntry | null;
  workouts: Workout[];
};

type AttentionItem = {
  athleteId: number;
  name: string;
  reason: string;
  severity: "high" | "med" | "low";
};

function deriveAttention(
  roster: CoachAthleteListItem[],
  dayData: Map<number, AthleteDayData>,
): AttentionItem[] {
  const items: AttentionItem[] = [];
  for (const row of roster) {
    const data = dayData.get(row.athlete.id);
    if (!data) continue;
    const name = row.athlete.name;
    const skipped = data.workouts.filter((w) => w.status === "skipped");
    if (skipped.length > 0) {
      items.push({
        athleteId: row.athlete.id,
        name,
        reason: `${skipped.length} session${skipped.length > 1 ? "s" : ""} skipped`,
        severity: "high",
      });
      continue;
    }
    if (!data.recovery) {
      items.push({
        athleteId: row.athlete.id,
        name,
        reason: "No recovery logged today",
        severity: "med",
      });
      continue;
    }
    if (data.recovery.readiness_score != null && data.recovery.readiness_score < 55) {
      items.push({
        athleteId: row.athlete.id,
        name,
        reason: `Readiness ${data.recovery.readiness_score}`,
        severity: "high",
      });
      continue;
    }
    if (data.workouts.length === 0) {
      items.push({
        athleteId: row.athlete.id,
        name,
        reason: "No session planned today",
        severity: "low",
      });
    }
  }
  const order = { high: 0, med: 1, low: 2 };
  return items.sort((a, b) => order[a.severity] - order[b.severity]);
}

export function CoachTodayPage() {
  const today = todayIso();
  const [roster, setRoster] = useState<CoachAthleteListItem[]>([]);
  const [dayData, setDayData] = useState<Map<number, AthleteDayData>>(new Map());
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [filter, setFilter] = useState<"all" | "high" | "med">("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listAthletes().then(async (result) => {
      if (cancelled) return;
      if (!result.success || !result.athletes) {
        setError(result.error ?? "Failed to load athletes");
        setLoading(false);
        return;
      }
      setRoster(result.athletes);
      const map = new Map<number, AthleteDayData>();
      await Promise.all(
        result.athletes.map(async (row) => {
          const id = row.athlete.id;
          const [recoveryResult, calendarResult] = await Promise.all([
            getAthleteTodayEntry(id),
            getAthleteCalendar(id, today, today),
          ]);
          map.set(id, {
            athleteId: id,
            recovery:
              recoveryResult.success && recoveryResult.entry ? recoveryResult.entry : null,
            workouts: calendarResult.success ? calendarResult.workouts : [],
          });
        }),
      );
      if (cancelled) return;
      setDayData(map);
      if (result.athletes.length > 0) {
        setSelectedId(result.athletes[0].athlete.id);
      }
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [today]);

  const attention = useMemo(() => deriveAttention(roster, dayData), [roster, dayData]);
  const filteredAttention = useMemo(() => {
    if (filter === "all") return attention;
    return attention.filter((item) => item.severity === filter);
  }, [attention, filter]);

  const selected = selectedId != null ? dayData.get(selectedId) : undefined;
  const selectedAthlete = roster.find((r) => r.athlete.id === selectedId)?.athlete;

  return (
    <PageFrame title="Coach · Today" question="Who needs my attention today?">
      {loading && <p className="text-sm text-slate-500">Loading roster…</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="grid gap-3 md:grid-cols-[320px_minmax(0,1fr)]">
        <SectionBox label="Attention Queue" note="derived · severity">
          <div className="mb-2 flex flex-wrap gap-1">
            {(["all", "high", "med"] as const).map((key) => (
              <button
                key={key}
                type="button"
                className={filter === key ? undefined : "secondary"}
                onClick={() => setFilter(key)}
              >
                {key === "all" ? "All" : key === "high" ? "High" : "Med"}
              </button>
            ))}
          </div>
          {filteredAttention.length === 0 ? (
            <p className="text-sm text-slate-500">No flags right now.</p>
          ) : (
            <ul className="divide-y divide-slate-100 text-sm">
              {filteredAttention.map((item) => (
                <li key={`${item.athleteId}-${item.reason}`}>
                  <button
                    type="button"
                    className="flex w-full items-center justify-between py-2 text-left"
                    onClick={() => setSelectedId(item.athleteId)}
                  >
                    <span>
                      <span className="mr-1 text-slate-400">
                        {item.severity === "high" ? "●" : "○"}
                      </span>
                      {item.name} — {item.reason}
                    </span>
                    <span className="text-slate-400">›</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          <div className="mt-3">
            <Link to="/athletes" className="button-link">
              Manage athletes
            </Link>
          </div>
        </SectionBox>

        <SectionBox label="Selected Athlete · Preview" note="triage without leaving Today">
          {selectedAthlete && selected ? (
            <>
              <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
                <div className="text-sm font-semibold text-slate-900">{selectedAthlete.name}</div>
                <Link to={`/coach/athletes/${selectedAthlete.id}`} className="button-link">
                  Open athlete
                </Link>
              </div>
              <SectionRow cols={4}>
                <Chip>
                  Readiness {selected.recovery?.readiness_score ?? "—"}
                </Chip>
                <Chip>{selected.workouts.length} session(s)</Chip>
                <Chip>
                  {selected.workouts[0]?.status ?? "no plan"}
                </Chip>
                <ReadinessBadge score={selected.recovery?.readiness_score ?? null} />
              </SectionRow>
              <div className="mt-3">
                <div className="mb-1 text-[11px] uppercase text-slate-400">Why flagged</div>
                <p className="rounded border border-slate-200 bg-slate-50 p-2 text-sm text-slate-700">
                  {attention.find((a) => a.athleteId === selectedAthlete.id)?.reason ??
                    "Selected from roster — no active flag."}
                </p>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <button type="button" className="secondary" disabled>
                  Message
                </button>
                <Link to={`/coach/athletes/${selectedAthlete.id}`} className="button-link">
                  Adjust plan
                </Link>
                <button type="button" className="secondary" disabled>
                  Mark reviewed
                </button>
              </div>
            </>
          ) : (
            <p className="text-sm text-slate-500">Select an athlete from the queue or roster.</p>
          )}
        </SectionBox>
      </div>

      <SectionBox label="Today's Sessions · Roster" note="planned status">
        <div className="grid grid-cols-[1fr_1fr_1fr_1fr_80px] gap-2 border-b border-slate-200 pb-1 text-[10px] uppercase text-slate-400">
          <div>Athlete</div>
          <div>Planned</div>
          <div>Status</div>
          <div>Recovery</div>
          <div />
        </div>
        {roster.length === 0 && !loading ? (
          <p className="py-3 text-sm text-slate-500">No athletes on your roster yet.</p>
        ) : (
          roster.map((row) => {
            const data = dayData.get(row.athlete.id);
            const workout = data?.workouts[0];
            return (
              <button
                key={row.athlete.id}
                type="button"
                className="grid w-full grid-cols-[1fr_1fr_1fr_1fr_80px] items-center gap-2 border-b border-slate-100 py-2 text-left text-sm"
                onClick={() => setSelectedId(row.athlete.id)}
              >
                <div className="font-medium text-slate-900">{row.athlete.name}</div>
                <div className="text-slate-600">{workout?.title ?? "—"}</div>
                <div>
                  <Chip>{workout?.status ?? "none"}</Chip>
                </div>
                <div className="text-slate-600">
                  {data?.recovery?.readiness_score ?? "—"}
                </div>
                <div className="text-right text-slate-400">›</div>
              </button>
            );
          })
        )}
      </SectionBox>

      <SectionRow cols={2}>
        <SectionBox label="Unread Notes" note="placeholder">
          <ul className="divide-y divide-slate-100 text-sm text-slate-600">
            <li className="py-1.5">Notes from athletes will appear here.</li>
          </ul>
        </SectionBox>
        <SectionBox label="AI Feed" note="placeholder">
          <ul className="divide-y divide-slate-100 text-sm text-slate-600">
            <li className="py-1.5">Cross-roster insights will appear here.</li>
          </ul>
        </SectionBox>
      </SectionRow>
    </PageFrame>
  );
}
