import { useEffect, useMemo, useState } from "react";
import {
  getMyPosition,
  listMyPlans,
  type AthletePosition,
  type TrainingPlan,
} from "../planning/api";
import { buildPlanView } from "../planning/domain";
import { AthleteCycleView } from "../planning/cycle/AthleteCycleView";
import { MetaLine } from "../planning/cycle/CyclePrimitives";
import { PageFrame } from "../shared/PageChrome";

export function AthletePlanPage() {
  const [plans, setPlans] = useState<TrainingPlan[]>([]);
  const [position, setPosition] = useState<AthletePosition | null>(null);
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([listMyPlans(), getMyPosition()]).then(([plansResult, positionResult]) => {
      if (cancelled) return;
      if (!plansResult.success) {
        setError(plansResult.error ?? "Failed to load plans");
        setPlans([]);
        setPosition(null);
        setSelectedPlanId(null);
      } else {
        setError(null);
        const list = plansResult.plans ?? [];
        setPlans(list);
        if (positionResult.success) {
          setPosition({
            plan: positionResult.plan ?? null,
            mesocycle: positionResult.mesocycle ?? null,
            microcycle: positionResult.microcycle ?? null,
            upcoming_items: positionResult.upcoming_items ?? [],
            coach_review: positionResult.coach_review ?? null,
          });
        } else {
          setPosition(null);
        }
        const fromPosition = positionResult.success ? positionResult.plan?.id : undefined;
        const active =
          list.find((p) => p.id === fromPosition) ?? list.find((p) => p.status === "active");
        setSelectedPlanId(active?.id ?? list[0]?.id ?? null);
      }
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const plan = plans.find((p) => p.id === selectedPlanId) ?? null;
  const view = useMemo(() => (plan ? buildPlanView(plan) : null), [plan]);

  return (
    <PageFrame title="Plan" question="Where am I in the cycle?">
      {loading && <p className="text-sm text-slate-500">Loading plan…</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      {!loading && !error && plans.length > 1 ? (
        <div className="mb-2">
          <select
            value={selectedPlanId ?? ""}
            onChange={(e) => setSelectedPlanId(Number(e.target.value))}
            className="rounded border border-slate-200 bg-white px-2 py-1.5 text-[12px] text-slate-800"
          >
            {plans.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
      ) : null}

      {!loading && !error && position?.plan && selectedPlanId === position.plan.id ? (
        <div className="mb-3 rounded-md border border-slate-900/20 bg-slate-900/5 px-3 py-2">
          <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-slate-900">
            Current position
          </span>
          <MetaLine className="mt-0.5">
            {position.mesocycle?.name ?? "—"}
            {position.microcycle
              ? ` · ${position.microcycle.name ?? `Period ${position.microcycle.ordinal + 1}`}`
              : ""}
            {position.upcoming_items.length
              ? ` · ${position.upcoming_items.length} upcoming`
              : ""}
          </MetaLine>
        </div>
      ) : null}

      {!loading && !error && plan && view ? (
        <AthleteCycleView plan={plan} view={view} calendarHref="/activities" />
      ) : null}

      {!loading && !error && !plan ? (
        <div className="rounded-lg border border-dashed border-slate-200 p-6 text-center text-[13px] text-slate-500">
          No training plan assigned yet. Your coach will set one up.
        </div>
      ) : null}
    </PageFrame>
  );
}
