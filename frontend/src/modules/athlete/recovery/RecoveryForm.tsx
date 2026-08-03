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

/** Energy (1 flat → 10 fresh) maps inversely onto stored fatigue. */
function fatigueToEnergy(fatigue: number): number {
  return 11 - fatigue;
}

function energyToFatigue(energy: number): number {
  return 11 - energy;
}

type ScaleField = "fatigue" | "soreness" | "mood" | "sleep_quality";

function ScalePicker({
  label,
  hint,
  value,
  onChange,
  invertDisplay,
}: {
  label: string;
  hint: string;
  value: string;
  onChange: (next: string) => void;
  /** When true, UI shows energy (higher = better) while value stores fatigue. */
  invertDisplay?: boolean;
}) {
  const stored = value ? Number.parseInt(value, 10) : null;
  const selected =
    stored != null && !Number.isNaN(stored)
      ? invertDisplay
        ? fatigueToEnergy(stored)
        : stored
      : null;

  return (
    <div className="flex items-center gap-2">
      <div className="w-24 shrink-0 text-[11px] text-slate-500">{label}</div>
      <div className="flex flex-1 gap-1">
        {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => {
          const active = selected === n;
          return (
            <button
              key={n}
              type="button"
              className={`scale-chip flex-1 ${
                active ? "scale-chip-active" : ""
              }`}
              onClick={() =>
                onChange(String(invertDisplay ? energyToFatigue(n) : n))
              }
            >
              {n}
            </button>
          );
        })}
      </div>
      <div className="w-20 shrink-0 text-right text-[10px] text-slate-400">{hint}</div>
    </div>
  );
}

type RecoveryFormProps = {
  onSaved?: (entry: RecoveryEntry) => void;
  /** Prefill without a second fetch (Today page already loaded today's entry). */
  initialEntry?: RecoveryEntry | null;
  variant?: "default" | "check-in";
  onCancel?: () => void;
};

export function RecoveryForm({
  onSaved,
  initialEntry,
  variant = "default",
  onCancel,
}: RecoveryFormProps) {
  const isCheckIn = variant === "check-in";
  const [form, setForm] = useState<FormState>(() =>
    initialEntry ? entryToForm(initialEntry) : emptyForm(),
  );
  const [readinessScore, setReadinessScore] = useState<number | null>(
    initialEntry?.readiness_score ?? null,
  );
  const [loading, setLoading] = useState(initialEntry === undefined);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [optionalOpen, setOptionalOpen] = useState(false);

  useEffect(() => {
    if (initialEntry !== undefined) {
      setForm(initialEntry ? entryToForm(initialEntry) : emptyForm());
      setReadinessScore(initialEntry?.readiness_score ?? null);
      setLoading(false);
      return;
    }

    getTodayEntry().then(({ entry, error: loadError }) => {
      if (loadError) setError(loadError);
      if (entry) {
        setForm(entryToForm(entry));
        setReadinessScore(entry.readiness_score);
      }
      setLoading(false);
    });
  }, [initialEntry]);

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
      setError(result.error ?? "Failed to save check-in");
      return;
    }

    setReadinessScore(result.entry.readiness_score);
    setSuccess(isCheckIn ? "Check-in saved" : "Recovery entry saved");
    onSaved?.(result.entry);
  }

  if (loading) {
    return <p className="text-sm text-slate-500">{isCheckIn ? "Loading…" : "Loading recovery data…"}</p>;
  }

  const checkInScales: Array<{
    field: ScaleField;
    label: string;
    hint: string;
    invertDisplay?: boolean;
  }> = [
    { field: "fatigue", label: "Energy", hint: "flat → fresh", invertDisplay: true },
    { field: "sleep_quality", label: "Sleep quality", hint: "poor → great" },
    { field: "soreness", label: "Soreness", hint: "none → sore" },
    { field: "mood", label: "Mood", hint: "low → high" },
  ];

  if (isCheckIn) {
    return (
      <form className="stack recovery-form space-y-3" onSubmit={onSubmit}>
        <div className="mb-1">
          <div className="text-sm font-semibold text-slate-900">How are you today?</div>
          <div className="text-[11px] text-slate-500">Takes ~20s · no wearable required</div>
        </div>

        <div className="space-y-2">
          {checkInScales.map((s) => (
            <ScalePicker
              key={s.field}
              label={s.label}
              hint={s.hint}
              value={form[s.field]}
              invertDisplay={s.invertDisplay}
              onChange={(v) => updateField(s.field, v)}
            />
          ))}
        </div>

        <div className="rounded border border-dashed border-slate-200 p-2">
          <button
            type="button"
            className="mb-1 flex w-full items-center justify-between text-left"
            onClick={() => setOptionalOpen((v) => !v)}
          >
            <span className="text-[11px] uppercase text-slate-400">Optional metrics</span>
            <span className="text-[11px] text-slate-500">{optionalOpen ? "▴ collapse" : "▾ expand"}</span>
          </button>
          {optionalOpen && (
            <div className="form-grid mt-2">
              <label>
                RHR (bpm)
                <input
                  type="number"
                  min={20}
                  max={220}
                  value={form.resting_hr_bpm}
                  onChange={(e) => updateField("resting_hr_bpm", e.target.value)}
                />
              </label>
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
                Body battery
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={form.body_battery}
                  onChange={(e) => updateField("body_battery", e.target.value)}
                />
              </label>
              <label className="sm:col-span-2">
                Notes
                <input value={form.notes} onChange={(e) => updateField("notes", e.target.value)} />
              </label>
            </div>
          )}
        </div>

        {error && <p className="error">{error}</p>}
        {success && <p className="success">{success}</p>}

        <div className="flex flex-wrap items-center gap-2">
          <button type="submit" disabled={saving}>
            {saving ? "Saving…" : "Save Today's Check-in"}
          </button>
          {onCancel && (
            <button type="button" className="secondary" onClick={onCancel} disabled={saving}>
              Cancel
            </button>
          )}
        </div>
      </form>
    );
  }

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
