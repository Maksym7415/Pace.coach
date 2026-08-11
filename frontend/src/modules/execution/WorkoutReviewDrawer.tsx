import { useEffect, useState, type ReactNode } from "react";
import { AlertTriangle, Check, ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { formatActualLines, formatExpectedLines, formatPlannedLabel } from "./labels";
import {
  initialResponsesFromQuestions,
  type AthleteQuestion,
  type IssueResponse,
} from "./questions";
import { SEVERITY_LABEL } from "./severity";
import type { IssueSeverity } from "./types";

export type { IssueResponse };

/* ------------------------------------------------------------------ */
/* Entry point banner                                                  */
/* ------------------------------------------------------------------ */
export function WorkoutReviewBanner({
  count,
  onReview,
}: {
  count: number;
  onReview: () => void;
}) {
  if (count < 1) return null;
  return (
    <div className="flex flex-col gap-3 rounded-md border border-dashed border-slate-200 bg-slate-50 p-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-start gap-2">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-slate-500" />
        <div>
          <div className="text-sm font-medium text-slate-900">
            {count} execution {count === 1 ? "issue needs" : "issues need"} your input.
          </div>
          <div className="text-xs text-slate-500">Help your coach understand what happened.</div>
        </div>
      </div>
      <button type="button" className="secondary shrink-0" onClick={onReview}>
        Review issues
      </button>
    </div>
  );
}

export function WorkoutReviewedLine({ count }: { count: number }) {
  return (
    <div className="flex items-center gap-2 text-[11px] text-slate-500">
      <Check className="h-3 w-3" /> Reviewed · {count} {count === 1 ? "issue" : "issues"} explained
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Severity badge — subtle, no strong colors                           */
/* ------------------------------------------------------------------ */
export function IssueSeverityBadge({ severity }: { severity: IssueSeverity }) {
  return (
    <span
      className={cn(
        "badge badge-muted shrink-0 font-mono text-[10px] uppercase tracking-wider",
        severity === "critical" ? "text-slate-900" : "text-slate-500",
      )}
    >
      {SEVERITY_LABEL[severity]}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/* Workout Review drawer — paginates AthleteQuestions                  */
/* ------------------------------------------------------------------ */
export function WorkoutReviewDrawer({
  questions,
  contextLabel,
  sportCode = null,
  startIndex = 0,
  open,
  onOpenChange,
  onComplete,
}: {
  questions: AthleteQuestion[];
  contextLabel: string;
  sportCode?: string | null;
  startIndex?: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onComplete?: (responses: Record<number, IssueResponse>) => void | Promise<void>;
}) {
  const [index, setIndex] = useState(startIndex);
  const [done, setDone] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [responses, setResponses] = useState<Record<number, IssueResponse>>(() =>
    initialResponsesFromQuestions(questions),
  );

  useEffect(() => {
    if (open) {
      setIndex(Math.min(Math.max(0, startIndex), Math.max(0, questions.length - 1)));
      setDone(false);
      setSaving(false);
      setSaveError(null);
      setResponses(initialResponsesFromQuestions(questions));
    }
  }, [open, startIndex, questions]);

  const question = questions[index];
  const isLast = index === questions.length - 1;

  const setResponse = (patch: Partial<IssueResponse>) => {
    if (!question) return;
    setResponses((prev) => ({
      ...prev,
      [question.issue_id]: { ...prev[question.issue_id], ...patch },
    }));
  };

  const finish = async () => {
    // Include every question so unanswered ones are still marked responded.
    const payload: Record<number, IssueResponse> = {};
    for (const q of questions) {
      payload[q.issue_id] = responses[q.issue_id] ?? {};
    }
    setSaving(true);
    setSaveError(null);
    try {
      await onComplete?.(payload);
      setDone(true);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Failed to save responses");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="flex w-full flex-col gap-0 p-0">
        <SheetHeader className="space-y-2 border-b border-slate-200 p-5 pr-12 text-left">
          <SheetTitle>Workout Review</SheetTitle>
          <SheetDescription>{contextLabel}</SheetDescription>
          {!done && question ? (
            <div className="flex items-center gap-3 pt-1">
              <span className="text-[11px] uppercase tracking-wider text-slate-400">
                Issue {index + 1} of {questions.length}
              </span>
              <div className="flex flex-1 items-center gap-1">
                {questions.map((q, i) => (
                  <span
                    key={q.issue_id}
                    className={cn(
                      "h-1 flex-1 rounded-full",
                      i <= index ? "bg-slate-500" : "bg-slate-200",
                    )}
                  />
                ))}
              </div>
            </div>
          ) : null}
        </SheetHeader>

        {done || !question ? (
          <ReviewComplete count={questions.length} onDone={() => onOpenChange(false)} />
        ) : (
          <>
            <div className="min-h-0 flex-1 overflow-auto">
              <ExecutionIssueCard
                question={question}
                sportCode={sportCode}
                response={responses[question.issue_id] ?? {}}
                onChange={setResponse}
              />
            </div>

            <div className="flex flex-col gap-2 border-t border-slate-200 p-4">
              {saveError ? <p className="text-xs text-red-600">{saveError}</p> : null}
              <div className="flex items-center justify-between gap-2">
                <button
                  type="button"
                  className="secondary"
                  disabled={index === 0 || saving}
                  onClick={() => setIndex((i) => Math.max(0, i - 1))}
                >
                  <span className="inline-flex items-center gap-1">
                    <ChevronLeft className="h-4 w-4" /> Previous
                  </span>
                </button>
                {isLast ? (
                  <button type="button" disabled={saving} onClick={() => void finish()}>
                    {saving ? "Saving…" : "Finish review"}
                  </button>
                ) : (
                  <button type="button" disabled={saving} onClick={() => setIndex((i) => i + 1)}>
                    <span className="inline-flex items-center gap-1">
                      Next issue <ChevronRight className="h-4 w-4" />
                    </span>
                  </button>
                )}
              </div>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}

/* ------------------------------------------------------------------ */
/* Issue card — Analysis → Athlete Response → reserved discussion      */
/* ------------------------------------------------------------------ */
export function ExecutionIssueCard({
  question,
  sportCode = null,
  response,
  onChange,
}: {
  question: AthleteQuestion;
  sportCode?: string | null;
  response: IssueResponse;
  onChange: (patch: Partial<IssueResponse>) => void;
}) {
  const expected = formatExpectedLines(question.step.planned, sportCode);
  const actual = formatActualLines(question.step, sportCode);
  const stepLabel = formatPlannedLabel(question.step.planned, sportCode);

  return (
    <div className="divide-y divide-slate-100">
      <div className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-sm font-semibold tracking-tight text-slate-900">{stepLabel}</div>
            <div className="text-xs text-slate-500">{question.title}</div>
          </div>
          <IssueSeverityBadge severity={question.issue.severity} />
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3">
          <div className="rounded-md border border-slate-200 p-3">
            <div className="mb-1 text-[10px] uppercase tracking-wider text-slate-400">Expected</div>
            {expected.map((line) => (
              <div key={line} className="text-xs text-slate-700">
                {line}
              </div>
            ))}
          </div>
          <div className="rounded-md border border-slate-200 p-3">
            <div className="mb-1 text-[10px] uppercase tracking-wider text-slate-400">Actual</div>
            {actual.map((line) => (
              <div key={line} className="text-xs text-slate-700">
                {line}
              </div>
            ))}
          </div>
        </div>
      </div>

      <Slot label="Analysis">
        <p className="text-xs text-slate-800">{question.analysis}</p>
      </Slot>

      <Slot label="Your response">
        <p className="mb-3 text-xs text-slate-500">
          Your explanation helps your coach decide whether future training needs to change.
        </p>
        <div className="mb-2 text-sm font-medium text-slate-900">{question.prompt}</div>

        <div className="flex flex-wrap gap-1.5">
          {question.reasons.map((reason) => {
            const active = response.reason === reason;
            return (
              <button
                key={reason}
                type="button"
                onClick={() => onChange({ reason: active ? undefined : reason })}
                className={cn("reason-chip", active && "reason-chip-active")}
              >
                {reason}
              </button>
            );
          })}
        </div>

        {response.reason === "Other" ? (
          <input
            className="mt-3 w-full rounded-md border border-slate-200 px-3 py-2 text-xs"
            placeholder="Tell your coach what happened"
            value={response.otherText ?? ""}
            onChange={(e) => onChange({ otherText: e.target.value })}
          />
        ) : null}

        <div className="mt-3">
          <div className="mb-1 text-[11px] text-slate-400">Notes (optional)</div>
          <textarea
            rows={3}
            className="w-full rounded-md border border-slate-200 px-3 py-2 text-xs"
            placeholder="Anything else worth knowing?"
            value={response.notes ?? ""}
            onChange={(e) => onChange({ notes: e.target.value })}
          />
        </div>
      </Slot>

      <div className="p-5">
        <div className="rounded-md border border-dashed border-slate-200 p-4 text-center opacity-60">
          <div className="text-[10px] uppercase tracking-wider text-slate-400">
            Discussion · coming soon
          </div>
          <p className="mt-1 text-[11px] text-slate-500">
            AI insight, coach response and resolution will appear here.
          </p>
        </div>
      </div>
    </div>
  );
}

function Slot({ label, children }: { label: string; children: ReactNode }) {
  return (
    <section className="p-5">
      <div className="mb-2 text-[10px] uppercase tracking-wider text-slate-400">{label}</div>
      {children}
    </section>
  );
}

export function ReviewComplete({ count, onDone }: { count: number; onDone: () => void }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center">
      <div className="flex h-10 w-10 items-center justify-center rounded-full border border-slate-200">
        <Check className="h-5 w-5 text-slate-700" />
      </div>
      <div className="text-sm font-semibold text-slate-900">Review completed.</div>
      <p className="max-w-xs text-xs text-slate-500">
        Your explanations have been attached to {count === 1 ? "this issue" : "these issues"}. Your
        coach will see them together with the workout analysis.
      </p>
      <button type="button" className="mt-2" onClick={onDone}>
        Done
      </button>
    </div>
  );
}
