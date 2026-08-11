import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ActivitiesView } from "../activities/ActivitiesView";
import { listAthletes, type CoachAthleteListItem } from "../coaching/api";
import { PageFrame, SectionBox } from "../shared/PageChrome";

const STORAGE_KEY = "pace.coach.activitiesAthleteId";

export function CoachActivitiesPage() {
  const [roster, setRoster] = useState<CoachAthleteListItem[]>([]);
  const [athleteId, setAthleteId] = useState<number | null>(() => {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const n = Number(raw);
    return Number.isFinite(n) ? n : null;
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listAthletes().then((result) => {
      if (cancelled) return;
      if (!result.success || !result.athletes) {
        setError(result.error ?? "Failed to load athletes");
        setRoster([]);
        setLoading(false);
        return;
      }
      setRoster(result.athletes);
      setAthleteId((prev) => {
        if (prev != null && result.athletes.some((a) => a.athlete.id === prev)) {
          return prev;
        }
        const first = result.athletes[0]?.athlete.id ?? null;
        if (first != null) localStorage.setItem(STORAGE_KEY, String(first));
        else localStorage.removeItem(STORAGE_KEY);
        return first;
      });
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  function onSelectAthlete(id: number) {
    setAthleteId(id);
    localStorage.setItem(STORAGE_KEY, String(id));
  }

  const selected = roster.find((r) => r.athlete.id === athleteId)?.athlete;

  return (
    <PageFrame title="Activities" question="Was it executed well?">
      <SectionBox label="Athlete" note="Scope calendar and list to one athlete">
        {loading && <p className="text-sm text-slate-500">Loading roster…</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
        {!loading && !error && roster.length === 0 && (
          <p className="text-sm text-slate-500">
            No athletes yet.{" "}
            <Link to="/athletes" className="underline">
              Invite someone on the roster
            </Link>
            .
          </p>
        )}
        {!loading && !error && roster.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            <label className="text-xs text-slate-500" htmlFor="coach-activities-athlete">
              Viewing
            </label>
            <select
              id="coach-activities-athlete"
              className="rounded-md border border-slate-200 bg-white px-2 py-1.5 text-sm"
              value={athleteId ?? ""}
              onChange={(e) => onSelectAthlete(Number(e.target.value))}
            >
              {roster.map((row) => (
                <option key={row.athlete.id} value={row.athlete.id}>
                  {row.athlete.name} (@{row.athlete.username})
                </option>
              ))}
            </select>
            {selected ? (
              <Link
                to={`/coach/athletes/${selected.id}/activities`}
                className="text-xs text-slate-600 hover:underline"
              >
                Open athlete workspace →
              </Link>
            ) : null}
          </div>
        )}
      </SectionBox>

      {athleteId != null && selected ? (
        <ActivitiesView
          scope={{ type: "athlete", athleteId }}
          heading={`${selected.name} · Activities`}
          subheading="Was it executed well?"
          coachPlanning
          coachMode
        />
      ) : null}
    </PageFrame>
  );
}
