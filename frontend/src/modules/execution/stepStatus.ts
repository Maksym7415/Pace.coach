import type { ExecutionIssue, StepExecution, StepExecutionStatus } from "./types";

/** Presentation statuses derived from engine facts (status + issues). */
export type StepDisplayStatus =
  | "skipped"
  | "unmatched"
  | "cut_short"
  | "off_target"
  | "on_target";

export type StepDisplayMeta = {
  id: StepDisplayStatus;
  glyph: string;
  label: string;
};

export const STEP_DISPLAY_META: Record<StepDisplayStatus, StepDisplayMeta> = {
  skipped: { id: "skipped", glyph: "✕", label: "Skipped" },
  unmatched: { id: "unmatched", glyph: "?", label: "No data" },
  cut_short: { id: "cut_short", glyph: "↷", label: "Finished early" },
  off_target: { id: "off_target", glyph: "⚠", label: "Executed but outside target" },
  on_target: { id: "on_target", glyph: "✓", label: "Executed as planned" },
};

function hasCode(issues: ExecutionIssue[], code: string): boolean {
  return issues.some((i) => i.code === code);
}

function hasDimension(issues: ExecutionIssue[], dimension: string): boolean {
  return issues.some((i) => i.dimension === dimension);
}

/**
 * Derive scan-friendly status from StepExecution facts.
 * Reads issues rather than re-deriving thresholds so tuning stays in issues.py.
 * First match wins.
 */
export function deriveDisplayStatus(step: StepExecution): StepDisplayStatus {
  const status: StepExecutionStatus = step.status;
  const issues = step.issues ?? [];

  if (status === "not_executed" || status === "not_attempted") {
    return "skipped";
  }
  if (status === "unmatched") {
    return "unmatched";
  }
  if (hasCode(issues, "incomplete_duration_or_distance") || status === "partially_executed") {
    return "cut_short";
  }
  if (hasDimension(issues, "intensity") || status === "substituted") {
    return "off_target";
  }
  return "on_target";
}

export function isProblematicStep(step: StepExecution): boolean {
  return deriveDisplayStatus(step) !== "on_target";
}
