import { FormEvent, useEffect, useState } from "react";
import { getMyBaselines, upsertMyBaselines } from "./api";

type RecoveryBaselinesSectionProps = {
  athleteId?: number;
  coachMode?: boolean;
  getBaselines?: () => ReturnType<typeof getMyBaselines>;
  saveBaselines?: (data: {
    hrv_baseline_min?: number | null;
    hrv_baseline_max?: number | null;
    resting_hr_baseline?: number | null;
  }) => ReturnType<typeof upsertMyBaselines>;
};

export function RecoveryBaselinesSection({
  athleteId: _athleteId,
  coachMode = false,
  getBaselines = getMyBaselines,
  saveBaselines = upsertMyBaselines,
}: RecoveryBaselinesSectionProps) {
  const [hrvMin, setHrvMin] = useState("");
  const [hrvMax, setHrvMax] = useState("");
  const [restingHr, setRestingHr] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    getBaselines().then((result) => {
      if (result.success && result.baseline) {
        const b = result.baseline;
        setHrvMin(b.hrv_baseline_min != null ? String(b.hrv_baseline_min) : "");
        setHrvMax(b.hrv_baseline_max != null ? String(b.hrv_baseline_max) : "");
        setRestingHr(b.resting_hr_baseline != null ? String(b.resting_hr_baseline) : "");
      }
      setLoading(false);
    });
  }, [getBaselines]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);

    const result = await saveBaselines({
      hrv_baseline_min: hrvMin.trim() ? Number.parseFloat(hrvMin) : null,
      hrv_baseline_max: hrvMax.trim() ? Number.parseFloat(hrvMax) : null,
      resting_hr_baseline: restingHr.trim() ? Number.parseFloat(restingHr) : null,
    });

    setSaving(false);
    if (!result.success) {
      setError(result.error ?? "Failed to save baselines");
      return;
    }
    setSuccess("Recovery baselines saved");
  }

  function formatMetric(value: string, unit: string) {
    return value.trim() ? `${value} ${unit}` : "—";
  }

  return (
    <section className="card stack">
      <h2>Recovery baselines</h2>
      <p className="muted">
        {coachMode
          ? "Athlete physiological baselines used for readiness tracking."
          : "Your physiological baselines used for readiness calculations."}
      </p>

      {loading ? (
        <p className="muted">Loading…</p>
      ) : coachMode ? (
        <dl className="detail-list">
          <div>
            <dt>HRV baseline min</dt>
            <dd>{formatMetric(hrvMin, "ms")}</dd>
          </div>
          <div>
            <dt>HRV baseline max</dt>
            <dd>{formatMetric(hrvMax, "ms")}</dd>
          </div>
          <div>
            <dt>Resting HR baseline</dt>
            <dd>{formatMetric(restingHr, "bpm")}</dd>
          </div>
        </dl>
      ) : (
        <form className="stack" onSubmit={onSubmit}>
          <div className="form-grid">
            <label>
              HRV baseline min (ms)
              <input
                type="number"
                min={0}
                step={0.1}
                value={hrvMin}
                onChange={(e) => setHrvMin(e.target.value)}
              />
            </label>
            <label>
              HRV baseline max (ms)
              <input
                type="number"
                min={0}
                step={0.1}
                value={hrvMax}
                onChange={(e) => setHrvMax(e.target.value)}
              />
            </label>
            <label>
              Resting HR baseline (bpm)
              <input
                type="number"
                min={20}
                max={220}
                value={restingHr}
                onChange={(e) => setRestingHr(e.target.value)}
              />
            </label>
          </div>
          {error && <p className="error">{error}</p>}
          {success && <p className="success">{success}</p>}
          <button type="submit" disabled={saving}>
            {saving ? "Saving…" : "Save baselines"}
          </button>
        </form>
      )}
    </section>
  );
}
