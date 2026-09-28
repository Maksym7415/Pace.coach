import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { createPlan, listAthletePlans, type TrainingPlan } from "../../planning/api";
import { CycleDesigner } from "../../planning/cycle/CycleDesigner";
import { NewPlanDialog } from "../../planning/cycle/CycleDialogs";
import { GhostButton, MetaLine } from "../../planning/cycle/CyclePrimitives";
import { useAthleteWorkspace } from "./AthleteWorkspaceLayout";

export function AthletePlanPage() {
  const { athleteId } = useAthleteWorkspace();
  const [searchParams] = useSearchParams();
  const [plans, setPlans] = useState<TrainingPlan[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newPlanOpen, setNewPlanOpen] = useState(false);

  const focus = {
    ...(searchParams.get("meso") ? { mesoId: Number(searchParams.get("meso")) } : {}),
    ...(searchParams.get("micro") ? { microId: Number(searchParams.get("micro")) } : {}),
    ...(searchParams.get("item") ? { itemId: Number(searchParams.get("item")) } : {}),
  };

  const loadPlans = () => {
    setLoading(true);
    listAthletePlans(athleteId).then((result) => {
      if (!result.success) {
        setError(result.error ?? "Failed to load plans");
        setPlans([]);
        setSelectedPlanId(null);
      } else {
        setError(null);
        const list = result.plans ?? [];
        setPlans(list);
        setSelectedPlanId((current) => {
          if (current && list.some((p) => p.id === current)) return current;
          const active = list.find((p) => p.status === "active");
          return active?.id ?? list[0]?.id ?? null;
        });
      }
      setLoading(false);
    });
  };

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    listAthletePlans(athleteId).then((result) => {
      if (cancelled) return;
      if (!result.success) {
        setError(result.error ?? "Failed to load plans");
        setPlans([]);
        setSelectedPlanId(null);
      } else {
        setError(null);
        const list = result.plans ?? [];
        setPlans(list);
        const active = list.find((p) => p.status === "active");
        setSelectedPlanId(active?.id ?? list[0]?.id ?? null);
      }
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [athleteId]);

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          {plans.length > 1 ? (
            <select
              value={selectedPlanId ?? ""}
              onChange={(e) => setSelectedPlanId(Number(e.target.value))}
              className="rounded border border-slate-200 bg-white px-2 py-1.5 text-[12px] text-slate-800"
            >
              {plans.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                  {p.status === "active" ? " · active" : ""}
                </option>
              ))}
            </select>
          ) : null}
          {plans.length === 1 ? (
            <MetaLine>
              {plans[0]?.name}
              {plans[0]?.status === "active" ? " · active" : ""}
            </MetaLine>
          ) : null}
        </div>
        <GhostButton tone="primary" onClick={() => setNewPlanOpen(true)}>
          + New training plan
        </GhostButton>
      </div>

      {loading && <p className="text-sm text-slate-500">Loading plans…</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      {!loading && !error && !selectedPlanId ? (
        <div className="rounded-lg border border-dashed border-slate-200 p-6 text-center">
          <p className="text-[13px] text-slate-500">
            No training plan yet. Start with architecture — blocks first, detail later.
          </p>
          <div className="mt-3 flex justify-center">
            <GhostButton tone="primary" onClick={() => setNewPlanOpen(true)}>
              + Create first plan
            </GhostButton>
          </div>
        </div>
      ) : null}

      {selectedPlanId ? (
        <CycleDesigner
          athleteId={athleteId}
          planId={selectedPlanId}
          focus={focus}
          onRequestNewPlan={() => setNewPlanOpen(true)}
        />
      ) : null}

      <NewPlanDialog
        open={newPlanOpen}
        onOpenChange={setNewPlanOpen}
        onCreate={async ({ title, goal, startDate, targetDate }) => {
          const result = await createPlan({
            athlete_id: athleteId,
            name: title,
            goal,
            ...(startDate ? { start_date: startDate } : {}),
            ...(targetDate ? { goal_event_date: targetDate } : {}),
          });
          if (!result.success || !result.plan) {
            setError(result.error ?? "Failed to create plan");
            return;
          }
          setSelectedPlanId(result.plan.id);
          loadPlans();
        }}
      />
    </div>
  );
}
