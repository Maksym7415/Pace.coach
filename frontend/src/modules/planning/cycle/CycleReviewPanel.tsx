import { useEffect, useState } from "react";
import type { CoachReview, SystemAnalysis } from "../api";
import { GhostButton, SectionLabel } from "./CyclePrimitives";

export function CycleReviewPanel({
  mesoName,
  analysis,
  review,
  onGenerateAnalysis,
  onCreateReview,
  onUpdateReview,
  onApprove,
  onNewVersion,
}: {
  mesoName: string;
  analysis: SystemAnalysis | null;
  review: CoachReview | null;
  onGenerateAnalysis?: () => void;
  onCreateReview: (opts: { fromAnalysis: boolean }) => void;
  onUpdateReview: (patch: { content?: string; next_cycle_focus?: string }) => void;
  onApprove: () => void;
  onNewVersion: () => void;
}) {
  const [focusDraft, setFocusDraft] = useState(review?.next_cycle_focus ?? "");

  useEffect(() => {
    setFocusDraft(review?.next_cycle_focus ?? "");
  }, [review?.id, review?.next_cycle_focus]);

  if (!analysis && !review) {
    return (
      <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50/50 p-4">
        <SectionLabel>Cycle review</SectionLabel>
        <p className="text-[13px] text-slate-500">
          The review opens once this block has been executed. A cycle ends with a review, not with
          its last workout.
        </p>
        {onGenerateAnalysis ? (
          <div className="mt-2">
            <GhostButton onClick={onGenerateAnalysis}>Generate system analysis</GhostButton>
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <SectionLabel
        right={
          <span className="text-[11px] text-slate-500">
            {review?.status === "approved"
              ? "Approved"
              : review
                ? "Draft in progress"
                : "Ready for review"}
          </span>
        }
      >
        Cycle review · {mesoName}
      </SectionLabel>

      {analysis ? (
        <section className="mb-3 rounded-md border border-slate-200 bg-slate-50 p-3">
          <div className="mb-1.5 flex items-baseline justify-between gap-2">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-slate-500">
              System analysis
            </div>
            <span className="rounded border border-slate-200 px-1.5 py-0.5 text-[10px] text-slate-500">
              immutable · generated {analysis.generated_at ?? "—"}
            </span>
          </div>
          <p className="text-[13px] leading-relaxed text-slate-700">
            {analysis.summary ?? "No summary available."}
          </p>
          <p className="mt-2 text-[11px] text-slate-500">
            Historical evidence. It is never edited or overwritten — a coach review is a separate
            record.
          </p>
        </section>
      ) : onGenerateAnalysis ? (
        <div className="mb-3">
          <GhostButton onClick={onGenerateAnalysis}>Generate system analysis</GhostButton>
        </div>
      ) : null}

      <section className="rounded-md border border-slate-200 p-3">
        <div className="mb-1.5 flex items-baseline justify-between gap-2">
          <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-slate-500">
            Coach review
          </div>
          {review ? (
            <span
              className={
                review.status === "approved"
                  ? "rounded border border-slate-900/30 bg-slate-900/5 px-1.5 py-0.5 text-[10px] text-slate-900"
                  : "rounded border border-amber-300 bg-amber-50 px-1.5 py-0.5 text-[10px] text-amber-700"
              }
            >
              {review.status === "approved"
                ? `Approved ${review.approved_at ?? ""}`
                : "Draft — not visible to athlete"}
            </span>
          ) : (
            <span className="text-[11px] text-slate-500">Not yet reviewed</span>
          )}
        </div>

        {!review ? (
          <div className="flex flex-wrap gap-2">
            {analysis ? (
              <GhostButton tone="primary" onClick={() => onCreateReview({ fromAnalysis: true })}>
                Use System Analysis
              </GhostButton>
            ) : null}
            <GhostButton onClick={() => onCreateReview({ fromAnalysis: false })}>
              Write my own review
            </GhostButton>
          </div>
        ) : review.status === "draft" ? (
          <div className="grid gap-2">
            {review.source_analysis_id ? (
              <p className="text-[11px] text-slate-500">
                Started from the system analysis. Edits here belong to your review only.
              </p>
            ) : null}
            <textarea
              value={review.content ?? ""}
              onChange={(e) => onUpdateReview({ content: e.target.value })}
              rows={5}
              placeholder="What did we learn from this cycle?"
              className="w-full resize-y rounded-md border border-slate-200 bg-white p-2 text-[13px] leading-relaxed outline-none focus:border-slate-400"
            />
            <label className="grid gap-1">
              <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-slate-500">
                Next cycle focus
              </span>
              <input
                value={focusDraft}
                onChange={(e) => {
                  setFocusDraft(e.target.value);
                  onUpdateReview({ next_cycle_focus: e.target.value });
                }}
                placeholder="Maintain threshold stimulus while reducing overall load."
                className="w-full rounded-md border border-slate-200 bg-white px-2 py-1.5 text-[13px] outline-none focus:border-slate-400"
              />
            </label>
            <div className="flex gap-2">
              <GhostButton
                tone="primary"
                disabled={!review.content?.trim()}
                onClick={onApprove}
              >
                Approve review
              </GhostButton>
            </div>
          </div>
        ) : (
          <div className="grid gap-2">
            <p className="text-[13px] leading-relaxed text-slate-700">{review.content}</p>
            {review.next_cycle_focus ? (
              <div className="rounded-md border border-slate-200 bg-slate-50 p-2">
                <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-slate-500">
                  Next cycle focus
                </div>
                <p className="mt-0.5 text-[13px] text-slate-700">{review.next_cycle_focus}</p>
                <p className="mt-1 text-[11px] text-slate-500">
                  Context for designing the next block — it does not change the plan.
                </p>
              </div>
            ) : null}
            <div>
              <GhostButton onClick={onNewVersion}>Edit review</GhostButton>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
