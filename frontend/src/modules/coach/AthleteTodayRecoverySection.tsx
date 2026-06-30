import { useEffect, useState } from "react";
import { ReadinessBadge } from "../athlete/recovery/ReadinessBadge";
import { getAthleteTodayEntry, type RecoveryEntry } from "../recovery/api";

type AthleteTodayRecoverySectionProps = {
  athleteId: number;
};

function formatMetric(value: number | null | undefined, unit: string): string {
  return value != null ? `${value} ${unit}` : "—";
}

export function AthleteTodayRecoverySection({ athleteId }: AthleteTodayRecoverySectionProps) {
  const [entry, setEntry] = useState<RecoveryEntry | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAthleteTodayEntry(athleteId).then((result) => {
      if (!result.success) {
        setError(result.error ?? "Failed to load today's recovery");
      } else {
        setEntry(result.entry ?? null);
      }
      setLoading(false);
    });
  }, [athleteId]);

  return (
    <section className="card stack">
      <div className="row-between">
        <h2>Today&apos;s recovery</h2>
        {!loading && !error && <ReadinessBadge score={entry?.readiness_score ?? null} />}
      </div>
      <p className="muted">Latest HRV and resting heart rate logged by the athlete.</p>

      {loading ? (
        <p className="muted">Loading…</p>
      ) : error ? (
        <p className="error">{error}</p>
      ) : !entry ? (
        <p className="muted">No recovery logged for today yet.</p>
      ) : (
        <dl className="detail-list">
          <div>
            <dt>HRV</dt>
            <dd>{formatMetric(entry.hrv_ms, "ms")}</dd>
          </div>
          <div>
            <dt>Resting HR</dt>
            <dd>{formatMetric(entry.resting_hr_bpm, "bpm")}</dd>
          </div>
        </dl>
      )}
    </section>
  );
}
