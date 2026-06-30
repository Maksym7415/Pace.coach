import { FormEvent, useEffect, useState } from "react";
import {
  addMyBodyMetric,
  listMyBodyMetrics,
  type BodyMetric,
} from "./api";
import { formatDate, todayIso } from "../shared/dates";

export function PersonalInfoSection() {
  const [weightKg, setWeightKg] = useState("");
  const [heightCm, setHeightCm] = useState("");
  const [measuredAt, setMeasuredAt] = useState(todayIso());
  const [history, setHistory] = useState<BodyMetric[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function loadHistory() {
    const result = await listMyBodyMetrics(3);
    if (result.success && result.metrics) {
      setHistory(result.metrics);
      const latest = result.metrics[0];
      if (latest) {
        setWeightKg(latest.weight_kg != null ? String(latest.weight_kg) : "");
        setHeightCm(latest.height_cm != null ? String(latest.height_cm) : "");
      }
    }
    setLoading(false);
  }

  useEffect(() => {
    loadHistory();
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);

    const weight = weightKg.trim() ? Number.parseFloat(weightKg) : null;
    const height = heightCm.trim() ? Number.parseFloat(heightCm) : null;

    if (weight == null && height == null) {
      setSaving(false);
      setError("Enter at least weight or height");
      return;
    }

    const result = await addMyBodyMetric({
      weight_kg: weight,
      height_cm: height,
      measured_at: measuredAt,
    });

    setSaving(false);
    if (!result.success) {
      setError(result.error ?? "Failed to save body metrics");
      return;
    }

    setSuccess("Body metrics saved");
    await loadHistory();
  }

  return (
    <section className="card stack">
      <h2>Personal information</h2>
      <p className="muted">
        Record weight and height. Each save creates a new history entry — previous values are
        preserved.
      </p>

      {loading ? (
        <p className="muted">Loading…</p>
      ) : (
        <form className="stack" onSubmit={onSubmit}>
          <div className="form-grid">
            <label>
              Weight (kg)
              <input
                type="number"
                min={0}
                step={0.1}
                value={weightKg}
                onChange={(e) => setWeightKg(e.target.value)}
              />
            </label>
            <label>
              Height (cm)
              <input
                type="number"
                min={0}
                step={0.1}
                value={heightCm}
                onChange={(e) => setHeightCm(e.target.value)}
              />
            </label>
            <label>
              Measured on
              <input
                type="date"
                value={measuredAt}
                onChange={(e) => setMeasuredAt(e.target.value)}
                required
              />
            </label>
          </div>
          {error && <p className="error">{error}</p>}
          {success && <p className="success">{success}</p>}
          <button type="submit" disabled={saving}>
            {saving ? "Saving…" : "Save measurement"}
          </button>
        </form>
      )}

      {history.length > 0 && (
        <div className="stack">
          <h3>Recent history</h3>
          <ul className="stack profile-history">
            {history.map((entry) => (
              <li key={entry.id} className="row-between">
                <span>{formatDate(entry.measured_at)}</span>
                <span className="muted">
                  {entry.weight_kg != null ? `${entry.weight_kg} kg` : "—"}
                  {" · "}
                  {entry.height_cm != null ? `${entry.height_cm} cm` : "—"}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
