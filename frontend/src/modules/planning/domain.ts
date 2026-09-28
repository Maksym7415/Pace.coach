/**
 * Cycle Designer view helpers.
 *
 * Consumes the server plan tree (dates, lock_state, gaps, conflicts already
 * computed). Never fabricates dates, period counts, or durations.
 */

import type {
  AnchorConflict,
  LockState,
  Mesocycle,
  Microcycle,
  PlanGap,
  PlanItem,
  TrainingPlan,
} from "./api";
import { todayIso } from "../shared/dates";

export type ExecutionState = "completed" | "issue" | "missed" | "planned";
export type TimeState = "past" | "current" | "future";

export type MicroView = {
  micro: Microcycle;
  mesoId: number;
  index: number;
  label: string;
  startDate?: string;
  endDate?: string;
  state: TimeState;
  locked: boolean;
  lockReason?: "historical" | "executed";
};

export type MesoView = {
  meso: Mesocycle;
  index: number;
  startDate?: string;
  endDate?: string;
  durationDays: number;
  periodCount: number;
  state: TimeState;
  locked: boolean;
  micros: MicroView[];
  anchorDate?: string;
  conflict?: AnchorConflict;
  gapBeforeDays?: number;
};

export type PlanView = {
  plan: TrainingPlan;
  dated: boolean;
  startDate?: string;
  endDate?: string;
  totalDays: number;
  periodCount: number;
  mesos: MesoView[];
  micros: MicroView[];
  current?: MicroView;
  currentMeso?: MesoView;
  nextMeso?: MesoView;
  progress: number;
  gaps: PlanGap[];
  conflicts: AnchorConflict[];
  targetDeltaDays?: number;
};

export function parseDate(iso: string): Date {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(y!, (m ?? 1) - 1, d ?? 1));
}

export function toISO(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export function addDays(iso: string, days: number): string {
  const d = parseDate(iso);
  d.setUTCDate(d.getUTCDate() + days);
  return toISO(d);
}

export function daysBetween(from: string, to: string): number {
  return Math.round((parseDate(to).getTime() - parseDate(from).getTime()) / 86400000);
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function formatDay(iso: string): string {
  const d = parseDate(iso);
  return `${MONTHS[d.getUTCMonth()]} ${d.getUTCDate()}`;
}

export function formatRange(start: string, end: string): string {
  const s = parseDate(start);
  const e = parseDate(end);
  if (s.getUTCMonth() === e.getUTCMonth()) {
    return `${MONTHS[s.getUTCMonth()]} ${s.getUTCDate()}–${e.getUTCDate()}`;
  }
  return `${formatDay(start)} – ${formatDay(end)}`;
}

export function formatMaybeRange(start?: string | null, end?: string | null): string | undefined {
  return start && end ? formatRange(start, end) : undefined;
}

function lockToTimeState(lock: LockState | null | undefined, start?: string | null, end?: string | null, today?: string): TimeState {
  if (lock === "locked") return "past";
  if (lock === "current") return "current";
  if (lock === "future") return "future";
  if (start && end && today) {
    if (end < today) return "past";
    if (start > today) return "future";
    return "current";
  }
  return "future";
}

export function microLabel(micro: Pick<Microcycle, "name">, weekIndex: number): string {
  if (micro.name) return micro.name;
  return `Week ${weekIndex + 1}`;
}

function itemSummary(item: PlanItem): string | undefined {
  const parts: string[] = [];
  if (item.planned_duration_min) parts.push(`${item.planned_duration_min} min`);
  if (item.planned_distance_m) {
    const km = item.planned_distance_m / 1000;
    parts.push(km >= 1 ? `${km % 1 === 0 ? km : km.toFixed(1)} km` : `${item.planned_distance_m} m`);
  }
  if (item.planned_workout_type) parts.push(item.planned_workout_type.replace(/_/g, " "));
  return parts.length ? parts.join(" · ") : undefined;
}

export function itemKind(item: PlanItem): "placeholder" | "workout" {
  return item.is_placeholder || item.workout_id == null ? "placeholder" : "workout";
}

export function itemPlannedLabel(item: PlanItem): string | undefined {
  if (itemKind(item) === "placeholder") return undefined;
  return itemSummary(item) ?? item.intent ?? undefined;
}

/**
 * Adapt a server plan tree into the designer view model.
 * Uses server dates, lock_state, gaps, and conflicts — never invents structure.
 */
export function buildPlanView(plan: TrainingPlan, today: string = todayIso()): PlanView {
  const dated = !!plan.start_date;
  const gaps = plan.gaps ?? [];
  const conflicts = plan.conflicts ?? [];
  const conflictByMeso = new Map(
    [
      ...conflicts.map((c) => [c.meso_id, c] as const),
      ...(plan.mesocycles ?? [])
        .filter((m) => m.conflict)
        .map((m) => [m.id, m.conflict!] as const),
    ],
  );
  const gapByMeso = new Map(gaps.map((g) => [g.meso_id, g]));

  let globalIndex = 0;
  const micros: MicroView[] = [];
  const mesocycles = [...(plan.mesocycles ?? [])].sort((a, b) => a.ordinal - b.ordinal);

  const mesos: MesoView[] = mesocycles.map((meso, mIdx) => {
    const mesoMicrosRaw = [...(meso.microcycles ?? [])].sort((a, b) => a.ordinal - b.ordinal);
    const mesoMicros: MicroView[] = mesoMicrosRaw.map((micro) => {
      const state = lockToTimeState(micro.lock_state, micro.start_date, micro.end_date, today);
      const locked = state === "past" || micro.lock_state === "locked";
      const view: MicroView = {
        micro,
        mesoId: meso.id,
        index: globalIndex,
        label: microLabel(micro, globalIndex),
        ...(micro.start_date ? { startDate: micro.start_date } : {}),
        ...(micro.end_date ? { endDate: micro.end_date } : {}),
        state,
        locked,
        ...(locked ? { lockReason: "historical" as const } : {}),
      };
      globalIndex += 1;
      micros.push(view);
      return view;
    });

    const durationDays =
      meso.duration_days ||
      mesoMicros.reduce((sum, m) => sum + Math.max(0, m.micro.duration_days), 0);
    const state = lockToTimeState(meso.lock_state, meso.start_date, meso.end_date, today);
    const gap = gapByMeso.get(meso.id);
    let gapBeforeDays = gap?.days;
    if (gapBeforeDays == null && mIdx > 0) {
      const prev = mesocycles[mIdx - 1];
      if (prev?.end_date && meso.start_date) {
        const derived = daysBetween(prev.end_date, meso.start_date) - 1;
        if (derived > 0) gapBeforeDays = derived;
      }
    }

    const conflict = conflictByMeso.get(meso.id) ?? undefined;

    return {
      meso,
      index: mIdx,
      ...(meso.start_date ? { startDate: meso.start_date } : {}),
      ...(meso.end_date ? { endDate: meso.end_date } : {}),
      durationDays,
      periodCount: mesoMicros.length,
      state,
      locked: state === "past" || meso.lock_state === "locked" || mesoMicros.some((m) => m.locked),
      micros: mesoMicros,
      ...(meso.anchor_date ? { anchorDate: meso.anchor_date } : {}),
      ...(conflict ? { conflict } : {}),
      ...(gapBeforeDays ? { gapBeforeDays } : {}),
    };
  });

  const totalDays = micros.reduce((sum, m) => sum + Math.max(0, m.micro.duration_days), 0);
  const startDate = plan.start_date ?? undefined;
  const endDate = plan.end_date ?? (micros.length ? micros[micros.length - 1]?.endDate : undefined);

  let progress = 0;
  if (startDate && endDate) {
    const span = daysBetween(startDate, endDate) + 1;
    const elapsed = daysBetween(startDate, today) + 1;
    progress = span > 0 ? Math.min(1, Math.max(0, elapsed / span)) : 0;
  }

  const current = micros.find((m) => m.state === "current");
  const currentMeso = mesos.find((m) => m.state === "current");
  const nextMeso = mesos.find((m) => m.state === "future");

  let targetDeltaDays: number | undefined;
  if (endDate && plan.goal_event_date) {
    targetDeltaDays = daysBetween(endDate, plan.goal_event_date);
  }

  return {
    plan,
    dated,
    ...(startDate ? { startDate } : {}),
    ...(endDate ? { endDate } : {}),
    totalDays,
    periodCount: micros.length,
    mesos,
    micros,
    ...(current ? { current } : {}),
    ...(currentMeso ? { currentMeso } : {}),
    ...(nextMeso ? { nextMeso } : {}),
    progress,
    gaps,
    conflicts: [...conflictByMeso.values()],
    ...(targetDeltaDays !== undefined ? { targetDeltaDays } : {}),
  };
}

export function planSummary(view: PlanView): string {
  const periods = view.periodCount;
  if (!periods) {
    return view.startDate
      ? `Starts ${formatDay(view.startDate)} · No periods`
      : "No periods · Start date not set";
  }
  const structure = `${view.totalDays} days · ${periods} period${periods === 1 ? "" : "s"}`;
  if (!view.startDate) return `${structure} · Start date not set`;
  const end = view.endDate ? ` → Projected end · ${formatDay(view.endDate)}` : "";
  return `${formatDay(view.startDate)}${end} · ${structure}`;
}

export function targetComparison(view: PlanView): string | undefined {
  if (!view.plan.goal_event_date || view.targetDeltaDays === undefined) return undefined;
  const d = view.targetDeltaDays;
  const target = `target ${formatDay(view.plan.goal_event_date)}`;
  if (d === 0) return `${target} · lands exactly on it`;
  if (d > 0) return `${target} · ${d} day${d === 1 ? "" : "s"} early`;
  return `${target} · ${-d} day${d === -1 ? "" : "s"} late`;
}

export function isItemLocked(_item: PlanItem, microState: TimeState, lockState?: LockState | null): boolean {
  if (microState === "past" || lockState === "locked") return true;
  return false;
}

export const EXECUTION_GLYPH: Record<ExecutionState, string> = {
  completed: "✓",
  issue: "⚠",
  missed: "✕",
  planned: "○",
};

export const TIME_GLYPH: Record<TimeState, string> = {
  past: "✓",
  current: "●",
  future: "○",
};
