/**
 * Athlete questions are presentation/workflow derived from ExecutionIssue facts.
 * Responses persist on ExecutionIssue via the athlete-responses API.
 */
import { formatPlannedLabel } from "./labels";
import { SEVERITY_RANK_SORT } from "./severity";
import type { ExecutionIssue, StepExecution, WorkoutExecution } from "./types";

export type IssueResponse = {
  reason?: string;
  otherText?: string;
  notes?: string;
};

export type AthleteQuestion = {
  issue_id: number;
  step: StepExecution;
  issue: ExecutionIssue;
  title: string;
  prompt: string;
  analysis: string;
  reasons: string[];
};

const DEFAULT_REASONS = [
  "Legs felt heavy",
  "Too hot",
  "Poor sleep",
  "Traffic / crossing",
  "Nutrition",
  "Device issue",
  "Pain",
  "Intentional",
  "Missed watch alert",
  "Other",
];

type IssueCopy = {
  title: string;
  prompt: (step: StepExecution) => string;
  analysis: (step: StepExecution, issue: ExecutionIssue) => string;
  reasons?: string[];
};

function stepName(step: StepExecution): string {
  return formatPlannedLabel(step.planned);
}

const ISSUE_COPY: Record<string, IssueCopy> = {
  below_target_adherence: {
    title: "Below target adherence",
    prompt: (step) => `What happened during this ${step.planned.step_type}?`,
    analysis: (step) => {
      const pct =
        step.time_in_target_pct != null ? `${Math.round(step.time_in_target_pct)}%` : "Low share";
      return `${pct} of time was spent in the planned target range.`;
    },
  },
  recovery_too_hard: {
    title: "Recovery too hard",
    prompt: () => "Why do you think recovery didn't go as planned?",
    analysis: () => "This recovery step ran harder than the planned target.",
    reasons: [
      "Still settling from the interval",
      "Legs felt heavy",
      "Intentional",
      "Missed watch alert",
      "Too hot",
      "Other",
    ],
  },
  incomplete_duration_or_distance: {
    title: "Finished early",
    prompt: () => "What happened at the end of this step?",
    analysis: () => "This step ended before the planned duration or distance was completed.",
  },
  step_not_executed: {
    title: "Step not executed",
    prompt: (step) => `Why was ${stepName(step)} skipped?`,
    analysis: () => "This planned step was not found in the recorded activity.",
  },
  step_not_attempted: {
    title: "Step not attempted",
    prompt: (step) => `Why wasn't ${stepName(step)} attempted?`,
    analysis: () => "This planned step was not attempted during the activity.",
  },
  step_unmatched: {
    title: "Could not match step",
    prompt: () => "Anything unusual about how this workout was recorded?",
    analysis: () => "The engine could not confidently match this planned step to recorded data.",
    reasons: ["Device issue", "Manual laps", "Workout not started on watch", "Other"],
  },
  step_substituted: {
    title: "Step substituted",
    prompt: () => "Did you intentionally change this step?",
    analysis: () => "A different structure was detected than the one that was planned.",
  },
  inconsistent_pacing: {
    title: "Inconsistent pacing",
    prompt: () => "What affected your pacing during this step?",
    analysis: () => "Pace varied more than expected across this step.",
  },
};

const FALLBACK_COPY: IssueCopy = {
  title: "Execution issue",
  prompt: () => "What happened during this step?",
  analysis: (step, issue) =>
    `An execution issue (${issue.code}) was detected on ${stepName(step)}.`,
};

function copyFor(code: string): IssueCopy {
  return ISSUE_COPY[code] ?? FALLBACK_COPY;
}

export function questionsForExecution(execution: WorkoutExecution): AthleteQuestion[] {
  const questions: AthleteQuestion[] = [];

  for (const step of execution.step_executions) {
    for (const issue of step.issues) {
      const copy = copyFor(issue.code);
      questions.push({
        issue_id: issue.id,
        step,
        issue,
        title: copy.title,
        prompt: copy.prompt(step),
        analysis: copy.analysis(step, issue),
        reasons: copy.reasons ?? DEFAULT_REASONS,
      });
    }
  }

  questions.sort((a, b) => {
    if (a.step.occurrence_ordinal !== b.step.occurrence_ordinal) {
      return a.step.occurrence_ordinal - b.step.occurrence_ordinal;
    }
    return SEVERITY_RANK_SORT[b.issue.severity] - SEVERITY_RANK_SORT[a.issue.severity];
  });

  return questions;
}

/** Seed drawer state from persisted athlete_response fields. */
export function initialResponsesFromQuestions(
  questions: AthleteQuestion[],
): Record<number, IssueResponse> {
  const out: Record<number, IssueResponse> = {};
  for (const q of questions) {
    const saved = q.issue.athlete_response;
    if (!saved) continue;
    out[q.issue_id] = {
      reason: saved.reason ?? undefined,
      otherText: saved.reason_other ?? undefined,
      notes: saved.notes ?? undefined,
    };
  }
  return out;
}

export function allIssuesResponded(execution: WorkoutExecution | null | undefined): boolean {
  if (!execution || execution.issue_count < 1) return false;
  return (execution.responded_issue_count ?? 0) >= execution.issue_count;
}

/** Index of the first question belonging to this step, or -1. */
export function firstQuestionIndexForStep(
  questions: AthleteQuestion[],
  step: StepExecution,
): number {
  return questions.findIndex(
    (q) =>
      q.step.authored_step_id === step.authored_step_id &&
      q.step.occurrence_ordinal === step.occurrence_ordinal,
  );
}
