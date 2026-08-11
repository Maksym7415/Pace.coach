import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useParams } from "react-router-dom";
import { getAthlete, type CoachAthleteDetail } from "../../coaching/api";
import { PageFrame } from "../../shared/PageChrome";

export type AthleteWorkspaceContextValue = {
  athleteId: number;
  detail: CoachAthleteDetail;
};

const AthleteWorkspaceContext = createContext<AthleteWorkspaceContextValue | null>(null);

export function useAthleteWorkspace(): AthleteWorkspaceContextValue {
  const ctx = useContext(AthleteWorkspaceContext);
  if (!ctx) {
    throw new Error("useAthleteWorkspace must be used within AthleteWorkspaceLayout");
  }
  return ctx;
}

const TABS = [
  { to: ".", end: true, label: "Overview" },
  { to: "plan", end: false, label: "Plan" },
  { to: "activities", end: false, label: "Activities" },
  { to: "performance", end: false, label: "Performance" },
  { to: "recovery", end: false, label: "Recovery" },
] as const;

export function AthleteWorkspaceLayout() {
  const { athleteId: athleteIdParam } = useParams<{ athleteId: string }>();
  const athleteId = Number(athleteIdParam);
  const [detail, setDetail] = useState<CoachAthleteDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!athleteId || Number.isNaN(athleteId)) {
      setError("Invalid athlete");
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    getAthlete(athleteId).then((result) => {
      if (cancelled) return;
      if (!result.success || !result.athlete) {
        setError(result.error ?? "Failed to load athlete");
        setDetail(null);
      } else {
        setDetail({
          relation_id: result.relation_id,
          coaching_since: result.coaching_since,
          athlete: result.athlete,
          upcoming_workouts_count: result.upcoming_workouts_count ?? 0,
        });
      }
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [athleteId]);

  const contextValue = useMemo(
    () => (detail ? { athleteId, detail } : null),
    [athleteId, detail],
  );

  if (loading) {
    return (
      <PageFrame title="Athlete" question="Loading workspace…">
        <p className="text-sm text-slate-500">Loading athlete…</p>
      </PageFrame>
    );
  }

  if (error || !detail || !contextValue) {
    return (
      <PageFrame title="Athlete" question="Who am I coaching?">
        <p className="text-sm text-red-600">{error ?? "Athlete not found"}</p>
        <Link to="/athletes" className="button-link">
          ← Back to athletes
        </Link>
      </PageFrame>
    );
  }

  const name = detail.athlete.name;

  return (
    <PageFrame title={name} question="Athlete workspace">
      <AthleteContextBar name={name} />
      <div className="mb-1 flex flex-wrap gap-1 border-b border-slate-200">
        {TABS.map((tab) => (
          <NavLink
            key={tab.label}
            to={tab.to}
            end={tab.end}
            className={({ isActive }) =>
              [
                "rounded-t-md px-3 py-2 text-xs",
                isActive
                  ? "border-b-2 border-slate-900 font-medium text-slate-900"
                  : "text-slate-500 hover:text-slate-800",
              ].join(" ")
            }
          >
            {tab.label}
          </NavLink>
        ))}
      </div>
      <AthleteWorkspaceContext.Provider value={contextValue}>
        <Outlet />
      </AthleteWorkspaceContext.Provider>
    </PageFrame>
  );
}

function AthleteContextBar({ name }: { name: string }) {
  const { pathname } = useLocation();
  const { athleteId } = useParams<{ athleteId: string }>();
  const section = sectionFromPath(pathname);
  return (
    <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
      <nav className="flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
        <Link to="/athletes" className="hover:text-slate-800">
          Athletes
        </Link>
        <span aria-hidden>›</span>
        <Link to={`/coach/athletes/${athleteId}`} className="hover:text-slate-800">
          {name}
        </Link>
        {section ? (
          <>
            <span aria-hidden>›</span>
            <span className="text-slate-800">{section}</span>
          </>
        ) : null}
      </nav>
      {section ? (
        <Link
          to={`/coach/athletes/${athleteId}`}
          className="rounded-md border border-slate-200 px-2.5 py-1 text-[11px] text-slate-500 hover:text-slate-800"
        >
          ← Athlete Overview
        </Link>
      ) : null}
    </div>
  );
}

function sectionFromPath(pathname: string): string | undefined {
  const match = pathname.match(/\/coach\/athletes\/[^/]+\/(plan|activities|performance|recovery)/);
  if (!match) return undefined;
  const map: Record<string, string> = {
    plan: "Plan",
    activities: "Activities",
    performance: "Performance",
    recovery: "Recovery",
  };
  return map[match[1]];
}
