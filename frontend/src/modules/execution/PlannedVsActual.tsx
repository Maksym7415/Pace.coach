import { cn } from "@/lib/utils";
import { Chip, SectionBox } from "../shared/PageChrome";
import { formatActualLabel, formatPlannedLabel } from "./labels";
import {
  deriveDisplayStatus,
  isProblematicStep,
  STEP_DISPLAY_META,
} from "./stepStatus";
import type { StepExecution, WorkoutExecution } from "./types";

function StepCard({
  step,
  sportCode,
  track,
  interactive,
  onSelect,
}: {
  step: StepExecution;
  sportCode: string | null;
  track: "planned" | "actual";
  interactive: boolean;
  onSelect?: (step: StepExecution) => void;
}) {
  const display = deriveDisplayStatus(step);
  const meta = STEP_DISPLAY_META[display];
  const problematic = isProblematicStep(step);
  const label =
    track === "planned"
      ? formatPlannedLabel(step.planned, sportCode)
      : formatActualLabel(step, sportCode);

  const content = (
    <>
      {track === "actual" ? (
        <div className="mb-1 flex items-center gap-1 text-[10px] uppercase tracking-wider text-slate-400">
          <span aria-hidden>{meta.glyph}</span>
          <span className={cn(problematic ? "text-slate-600" : "text-slate-400")}>
            {meta.label}
          </span>
        </div>
      ) : null}
      <div className="text-[11px] leading-snug text-slate-700">{label}</div>
      {track === "actual" && step.score != null ? (
        <div className="mt-1 text-[10px] text-slate-400">{Math.round(step.score)}</div>
      ) : null}
    </>
  );

  const className = cn(
    "min-w-0 rounded border border-slate-200 bg-slate-50 p-2 text-left",
    interactive && problematic && "cursor-pointer hover:border-slate-400 hover:bg-white",
    interactive && !problematic && "cursor-default",
  );

  if (interactive && problematic && onSelect) {
    return (
      <button
        type="button"
        className={className}
        onClick={() => onSelect(step)}
        aria-label={`Review issues for ${formatPlannedLabel(step.planned, sportCode)}`}
      >
        {content}
      </button>
    );
  }

  return <div className={className}>{content}</div>;
}

export function PlannedVsActual({
  execution,
  onSelectStep,
}: {
  execution: WorkoutExecution;
  onSelectStep?: (step: StepExecution) => void;
}) {
  const steps = execution.step_executions;
  const sportCode = execution.workout.sport_code;
  const columns = Math.max(steps.length, 1);
  const gridStyle = {
    gridTemplateColumns: `repeat(${columns}, minmax(7.5rem, 1fr))`,
  };

  if (!steps.length) {
    return (
      <SectionBox label="Planned vs Actual" note="workout steps">
        <p className="text-sm text-slate-500">No matched workout steps for this activity.</p>
      </SectionBox>
    );
  }

  return (
    <SectionBox label="Planned vs Actual" note="matched workout steps">
      <div className="mb-3 flex flex-wrap gap-1">
        <Chip>{execution.workout.title}</Chip>
        {execution.status ? <Chip>{execution.status}</Chip> : null}
        {execution.overall_confidence != null ? (
          <Chip>{Math.round(execution.overall_confidence * 100)}% match</Chip>
        ) : null}
        {execution.issue_count > 0 ? (
          <Chip>{execution.issue_count} issue{execution.issue_count === 1 ? "" : "s"}</Chip>
        ) : null}
      </div>

      <div className="overflow-x-auto">
        <div className="mb-1 text-[11px] text-slate-400">Planned</div>
        <div className="mb-3 grid gap-1" style={gridStyle}>
          {steps.map((step) => (
            <StepCard
              key={`p-${step.authored_step_id}-${step.occurrence_ordinal}`}
              step={step}
              sportCode={sportCode}
              track="planned"
              interactive={false}
            />
          ))}
        </div>

        <div className="mb-1 text-[11px] text-slate-400">Actual</div>
        <div className="grid gap-1" style={gridStyle}>
          {steps.map((step) => (
            <StepCard
              key={`a-${step.authored_step_id}-${step.occurrence_ordinal}`}
              step={step}
              sportCode={sportCode}
              track="actual"
              interactive={Boolean(onSelectStep)}
              onSelect={onSelectStep}
            />
          ))}
        </div>
      </div>
    </SectionBox>
  );
}
