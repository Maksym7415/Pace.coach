import { useCallback, useEffect, useState } from "react";
import { getPlan, type TrainingPlan } from "./api";

export function usePlan(planId: number | null | undefined) {
  const [plan, setPlan] = useState<TrainingPlan | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  const refresh = useCallback(() => setTick((t) => t + 1), []);

  useEffect(() => {
    if (!planId) {
      setPlan(null);
      setLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    getPlan(planId, "items").then((result) => {
      if (cancelled) return;
      if (!result.success || !result.plan) {
        setError(result.error ?? "Failed to load plan");
        setPlan(null);
      } else {
        setPlan(result.plan);
        setError(null);
      }
      setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, [planId, tick]);

  return { plan, loading, error, refresh, setPlan };
}
