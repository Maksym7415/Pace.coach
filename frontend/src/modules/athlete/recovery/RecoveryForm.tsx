import { FormEvent, useEffect, useState } from "react";
import {
  getTodayEntry,
  upsertEntry,
  type RecoveryEntry,
  type RecoveryEntryInput,
} from "../../recovery/api";
import { todayIso } from "../../shared/dates";
import { ReadinessBadge } from "./ReadinessBadge";

type FormState = {
  hrv_ms: string;
  resting_hr_bpm: string;
  body_battery: string;
  fatigue: string;
  soreness: string;
  mood: string;
  sleep_quality: string;
  sleep_hours: string;
  notes: string;
};

const emptyForm = (): FormState => ({
  hrv_ms: "",
  resting_hr_bpm: "",
  body_battery: "",
  fatigue: "",
  soreness: "",
  mood: "",
  sleep_quality: "",
  sleep_hours: "",
  notes: "",
});

function entryToForm(entry: RecoveryEntry): FormState {
  return {
    hrv_ms: entry.hrv_ms?.toString() ?? "",
    resting_hr_bpm: entry.resting_hr_bpm?.toString() ?? "",
    body_battery: entry.body_battery?.toString() ?? "",
    fatigue: entry.fatigue?.toString() ?? "",
    soreness: entry.soreness?.toString() ?? "",
    mood: entry.mood?.toString() ?? "",
    sleep_quality: entry.sleep_quality?.toString() ?? "",
    sleep_hours: entry.sleep_hours?.toString() ?? "",
    notes: entry.notes ?? "",
  };
}

function parseOptionalInt(value: string): number | null {
  if (!value.trim()) return null;
  const n = Number.parseInt(value, 10);
  return Number.isNaN(n) ? null : n;
}

function parseOptionalFloat(value: string): number | null {
  if (!value.trim()) return null;
  const n = Number.parseFloat(value);
  return Number.isNaN(n) ? null : n;
}

function buildPayload(form: FormState): RecoveryEntryInput {
  return {
    entry_date: todayIso(),
    hrv_ms: parseOptionalFloat(form.hrv_ms),
    resting_hr_bpm: parseOptionalInt(form.resting_hr_bpm),
    body_battery: parseOptionalInt(form.body_battery),
    fatigue: parseOptionalInt(form.fatigue),
    soreness: parseOptionalInt(form.soreness),
    mood: parseOptionalInt(form.mood),
    sleep_quality: parseOptionalInt(form.sleep_quality),
    sleep_hours: parseOptionalFloat(form.sleep_hours),
    notes: form.notes.trim() || null,
  };
}

type RecoveryFormProps = {
  onSaved?: (entry: RecoveryEntry) => void;
};

export function RecoveryForm({ onSaved }: RecoveryFormProps) {
  const [form, setForm] = useState<FormState>(emptyForm);
  const [readinessScore, setReadinessScore] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    getTodayEntry().then(({ entry, error: loadError }) => {
      if (loadError) setError(loadError);
      if (entry) {
        setForm(entryToForm(entry));
        setReadinessScore(entry.readiness_score);
      }
      setLoading(false);
    });
  }, []);

  function updateField(field: keyof FormState, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
    setSuccess(null);
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);

    const result = await upsertEntry(buildPayload(form));
    setSaving(false);

    if (!result.success || !result.entry) {
      setError(result.error ?? "Failed to save recovery entry");
      return;
    }

    setReadinessScore(result.entry.readiness_score);
    setSuccess("Recovery entry saved");
    onSaved?.(result.entry);
  }

  if (loading) return <p className="muted">Loading recovery data…</p>;

  return (
    <form className="stack recovery-form" onSubmit={onSubmit}>
      <div className="row-between">
        <h3>Today&apos;s recovery</h3>
        <ReadinessBadge score={readinessScore} />
      </div>

      <fieldset className="field-group">
        <legend>Objective</legend>
        <div className="form-grid">
          <label>
            HRV (ms)
            <input
              type="number"
              min={0}
              step={0.1}
              value={form.hrv_ms}
              onChange={(e) => updateField("hrv_ms", e.target.value)}
            />
          </label>
          <label>
            Resting HR (bpm)
            <input
              type="number"
              min={20}
              max={220}
              value={form.resting_hr_bpm}
              onChange={(e) => updateField("resting_hr_bpm", e.target.value)}
            />
          </label>
          <label>
            Body battery
            <input
              type="number"
              min={0}
              max={100}
              value={form.body_battery}
              onChange={(e) => updateField("body_battery", e.target.value)}
            />
          </label>
        </div>
      </fieldset>

      <fieldset className="field-group">
        <legend>Subjective</legend>
        <div className="form-grid">
          <label>
            Fatigue (1–10)
            <input
              type="range"
              min={1}
              max={10}
              value={form.fatigue || 5}
              onChange={(e) => updateField("fatigue", e.target.value)}
            />
            <span className="range-value">{form.fatigue || "—"}</span>
          </label>
          <label>
            Soreness (1–10)
            <input
              type="range"
              min={1}
              max={10}
              value={form.soreness || 5}
              onChange={(e) => updateField("soreness", e.target.value)}
            />
            <span className="range-value">{form.soreness || "—"}</span>
          </label>
          <label>
            Mood (1–10)
            <input
              type="range"
              min={1}
              max={10}
              value={form.mood || 5}
              onChange={(e) => updateField("mood", e.target.value)}
            />
            <span className="range-value">{form.mood || "—"}</span>
          </label>
          <label>
            Sleep quality (1–10)
            <input
              type="range"
              min={1}
              max={10}
              value={form.sleep_quality || 5}
              onChange={(e) => updateField("sleep_quality", e.target.value)}
            />
            <span className="range-value">{form.sleep_quality || "—"}</span>
          </label>
        </div>
      </fieldset>

      <div className="form-grid">
        <label>
          Sleep hours
          <input
            type="number"
            min={0}
            max={24}
            step={0.5}
            value={form.sleep_hours}
            onChange={(e) => updateField("sleep_hours", e.target.value)}
          />
        </label>
        <label>
          Notes
          <input value={form.notes} onChange={(e) => updateField("notes", e.target.value)} />
        </label>
      </div>

      {error && <p className="error">{error}</p>}
      {success && <p className="success">{success}</p>}

      <button type="submit" disabled={saving}>
        {saving ? "Saving…" : "Save recovery"}
      </button>
    </form>
  );
}
