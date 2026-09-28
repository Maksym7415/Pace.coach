import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { GhostButton, MetaLine } from "./CyclePrimitives";

const field =
  "rounded border border-slate-200 bg-white px-2 py-1.5 text-[12px] outline-none focus:border-slate-400";
const labelText = "font-mono text-[10px] uppercase tracking-[0.14em] text-slate-500";

export function NewPlanDialog({
  open,
  onOpenChange,
  onCreate,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onCreate: (v: { title: string; goal: string; startDate?: string; targetDate?: string }) => void;
}) {
  const [title, setTitle] = useState("");
  const [goal, setGoal] = useState("");
  const [startDate, setStartDate] = useState("");
  const [targetDate, setTargetDate] = useState("");

  useEffect(() => {
    if (open) {
      setTitle("");
      setGoal("");
      setStartDate("");
      setTargetDate("");
    }
  }, [open]);

  const create = (skipStart = false) => {
    onCreate({
      title: title.trim() || "New training plan",
      goal: goal.trim() || "Set a goal",
      ...(!skipStart && startDate ? { startDate } : {}),
      ...(targetDate ? { targetDate } : {}),
    });
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-[15px] tracking-tight">New training plan</DialogTitle>
          <DialogDescription className="text-[12px]">
            Architecture first. The end date is always derived from the structure you build.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-3">
          <label className="grid gap-1">
            <span className={labelText}>Plan name</span>
            <input
              autoFocus
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Autumn 10K Preparation"
              className={field}
            />
          </label>
          <label className="grid gap-1">
            <span className={labelText}>Goal</span>
            <input
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder="10K 36:00"
              className={field}
            />
          </label>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="grid gap-1">
              <span className={labelText}>Start date (optional)</span>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className={field}
              />
            </label>
            <label className="grid gap-1">
              <span className={labelText}>Target / race date (optional)</span>
              <input
                type="date"
                value={targetDate}
                onChange={(e) => setTargetDate(e.target.value)}
                className={field}
              />
            </label>
          </div>
          <MetaLine>
            No end date — it is projected from your blocks and periods. Without a start date the
            plan is built in durations only.
          </MetaLine>
        </div>

        <DialogFooter className="gap-1.5 sm:justify-start">
          <GhostButton tone="primary" onClick={() => create(false)}>
            Create plan
          </GhostButton>
          <GhostButton
            onClick={() => {
              setStartDate("");
              create(true);
            }}
          >
            Skip date — decide later
          </GhostButton>
          <GhostButton onClick={() => onOpenChange(false)}>Cancel</GhostButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export type MesocycleDraft = { name: string; intent: string; anchorDate?: string };

export function MesocycleDialog({
  open,
  onOpenChange,
  mode,
  initial,
  canAnchor,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  mode: "create" | "edit";
  initial?: MesocycleDraft;
  canAnchor: boolean;
  onSubmit: (draft: { name: string; intent: string; anchorDate: string | null }) => void;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [intent, setIntent] = useState(initial?.intent ?? "");
  const [anchorDate, setAnchorDate] = useState(initial?.anchorDate ?? "");

  useEffect(() => {
    if (open) {
      setName(initial?.name ?? "");
      setIntent(initial?.intent ?? "");
      setAnchorDate(initial?.anchorDate ?? "");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-[15px] tracking-tight">
            {mode === "create" ? "New training block" : "Edit training block"}
          </DialogTitle>
          <DialogDescription className="text-[12px]">
            A block can exist as intent alone — periods and workouts come later.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-3">
          <label className="grid gap-1">
            <span className={labelText}>Name</span>
            <input
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Base Development"
              className={field}
            />
          </label>
          <label className="grid gap-1">
            <span className={labelText}>Intent</span>
            <textarea
              value={intent}
              onChange={(e) => setIntent(e.target.value)}
              rows={2}
              placeholder="Establish consistent aerobic volume and running economy"
              className={field}
            />
          </label>
          {canAnchor ? (
            <label className="grid gap-1">
              <span className={labelText}>Start date anchor (optional)</span>
              <input
                type="date"
                value={anchorDate}
                onChange={(e) => setAnchorDate(e.target.value)}
                className={field}
              />
              <MetaLine>
                An anchor fixes this block to a date. Earlier periods reflow around it — it never
                moves on its own.
              </MetaLine>
            </label>
          ) : (
            <MetaLine>Set a plan start date to anchor blocks to the calendar.</MetaLine>
          )}
          <MetaLine>No end date — it derives from this block&apos;s periods.</MetaLine>
        </div>

        <DialogFooter className="gap-1.5 sm:justify-start">
          <GhostButton
            tone="primary"
            onClick={() => {
              onSubmit({
                name: name.trim() || "New block",
                intent: intent.trim() || "Describe the intent of this block",
                anchorDate: canAnchor && anchorDate ? anchorDate : null,
              });
              onOpenChange(false);
            }}
          >
            {mode === "create" ? "Add block" : "Save block"}
          </GhostButton>
          <GhostButton onClick={() => onOpenChange(false)}>Cancel</GhostButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function PlaceholderDialog({
  open,
  onOpenChange,
  initial,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  initial: { title: string; intent?: string | null };
  onSubmit: (draft: { title: string; intent: string | null }) => void;
}) {
  const [title, setTitle] = useState(initial.title);
  const [note, setNote] = useState(initial.intent ?? "");

  useEffect(() => {
    if (open) {
      setTitle(initial.title);
      setNote(initial.intent ?? "");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-[15px] tracking-tight">Edit placeholder</DialogTitle>
          <DialogDescription className="text-[12px]">
            A placeholder holds the coaching intent. Editing it never turns it into a workout.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-3">
          <label className="grid gap-1">
            <span className={labelText}>Intent / title</span>
            <input
              autoFocus
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Threshold session"
              className={field}
            />
          </label>
          <label className="grid gap-1">
            <span className={labelText}>Note (optional)</span>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={3}
              placeholder="Keep it controlled — decide the structure closer to the day"
              className={field}
            />
          </label>
          <MetaLine>
            Stays a placeholder in the same period and position. Convert to workout is a separate
            action.
          </MetaLine>
        </div>

        <DialogFooter className="gap-1.5 sm:justify-start">
          <GhostButton
            tone="primary"
            onClick={() => {
              onSubmit({
                title: title.trim() || "New session intent",
                intent: note.trim() || null,
              });
              onOpenChange(false);
            }}
          >
            Save placeholder
          </GhostButton>
          <GhostButton onClick={() => onOpenChange(false)}>Cancel</GhostButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function PlanDatesDialog({
  open,
  onOpenChange,
  startDate,
  targetDate,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  startDate?: string;
  targetDate?: string;
  onSubmit: (v: { startDate: string | null; targetDate: string | null }) => void;
}) {
  const [start, setStart] = useState(startDate ?? "");
  const [target, setTarget] = useState(targetDate ?? "");

  useEffect(() => {
    if (open) {
      setStart(startDate ?? "");
      setTarget(targetDate ?? "");
    }
  }, [open, startDate, targetDate]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-[15px] tracking-tight">Plan dates</DialogTitle>
          <DialogDescription className="text-[12px]">
            Dates derive from the structure you already built — nothing is rearranged.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="grid gap-1">
            <span className={labelText}>Start date</span>
            <input
              type="date"
              value={start}
              onChange={(e) => setStart(e.target.value)}
              className={field}
            />
          </label>
          <label className="grid gap-1">
            <span className={labelText}>Target / race date</span>
            <input
              type="date"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              className={field}
            />
          </label>
        </div>
        <DialogFooter className="gap-1.5 sm:justify-start">
          <GhostButton
            tone="primary"
            onClick={() => {
              onSubmit({ startDate: start || null, targetDate: target || null });
              onOpenChange(false);
            }}
          >
            Save dates
          </GhostButton>
          <GhostButton onClick={() => onOpenChange(false)}>Cancel</GhostButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
