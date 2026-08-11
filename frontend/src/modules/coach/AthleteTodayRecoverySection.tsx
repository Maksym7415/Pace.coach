import { useEffect, useState } from "react";
import { ReadinessBadge } from "../athlete/recovery/ReadinessBadge";
import { getAthleteTodayEntry, type RecoveryEntry } from "../recovery/api";

type AthleteTodayRecoverySectionProps = {
  athleteId: number;
  /** When true, omit outer card chrome (used inside SectionBox). */
  embedded?: boolean;
};

function formatMetric(value: number | null | undefined, unit: string): string {
  return value != null ? `${value} ${unit}` : "—";
}

function formatScore(value: number | null | undefined): string {
  return value != null ? String(value) : "—";
}

export function AthleteTodayRecoverySection({
  athleteId,
  embedded = false,
}: AthleteTodayRecoverySectionProps) {
  const [entry, setEntry] = useState<RecoveryEntry | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getAthleteTodayEntry(athleteId).then((result) => {
      if (!result.success) {
        setError(result.error ?? "Failed to load today's recovery");
      } else {
        setError(null);
        setEntry(result.entry ?? null);
      }
      setLoading(false);
    });
  }, [athleteId]);

  const body = (
    <>
      {!embedded && (
        <div className="row-between">
          <h2>Today&apos;s recovery</h2>
          {!loading && !error && <ReadinessBadge score={entry?.readiness_score ?? null} />}
        </div>
      )}
      {!embedded && (
        <p className="muted">Latest recovery signals logged by the athlete.</p>
      )}

      {embedded && !loading && !error && (
        <div className="mb-2 flex items-center justify-between gap-2">
          <span className="text-sm text-slate-600">Readiness</span>
          <ReadinessBadge score={entry?.readiness_score ?? null} />
        </div>
      )}

      {loading ? (
        <p className={embedded ? "text-sm text-slate-500" : "muted"}>Loading…</p>
      ) : error ? (
        <p className={embedded ? "text-sm text-red-600" : "error"}>{error}</p>
      ) : !entry ? (
        <p className={embedded ? "text-sm text-slate-500" : "muted"}>
          No recovery logged for today yet.
        </p>
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
          <div>
            <dt>Body battery</dt>
            <dd>{formatScore(entry.body_battery)}</dd>
          </div>
          <div>
            <dt>Sleep</dt>
            <dd>
              {entry.sleep_hours != null ? `${entry.sleep_hours} h` : "—"}
              {entry.sleep_quality != null ? ` · quality ${entry.sleep_quality}` : ""}
            </dd>
          </div>
          <div>
            <dt>Fatigue</dt>
            <dd>{formatScore(entry.fatigue)}</dd>
          </div>
          <div>
            <dt>Soreness</dt>
            <dd>{formatScore(entry.soreness)}</dd>
          </div>
          <div>
            <dt>Mood</dt>
            <dd>{formatScore(entry.mood)}</dd>
          </div>
          <div>
            <dt>Readiness score</dt>
            <dd>{formatScore(entry.readiness_score)}</dd>
          </div>
          {entry.notes ? (
            <div>
              <dt>Notes</dt>
              <dd>{entry.notes}</dd>
            </div>
          ) : null}
        </dl>
      )}
    </>
  );

  if (embedded) {
    return <div className="stack">{body}</div>;
  }

  return <section className="card stack">{body}</section>;
}
