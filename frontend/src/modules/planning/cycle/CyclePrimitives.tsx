import type { ReactNode } from "react";
import { EXECUTION_GLYPH, TIME_GLYPH, type ExecutionState, type TimeState } from "../domain";
import { cn } from "@/lib/utils";

export function StateDot({ state, className }: { state: TimeState; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex h-4 w-4 shrink-0 items-center justify-center text-[11px] leading-none",
        state === "past" && "text-slate-400",
        state === "current" && "text-slate-900",
        state === "future" && "text-slate-300",
        className,
      )}
      aria-hidden
    >
      {TIME_GLYPH[state]}
    </span>
  );
}

export function ExecutionDot({ state }: { state: ExecutionState }) {
  return (
    <span
      className={cn(
        "inline-flex h-4 w-4 shrink-0 items-center justify-center text-[11px] leading-none",
        state === "completed" && "text-slate-900",
        state === "issue" && "text-amber-600",
        state === "missed" && "text-red-600",
        state === "planned" && "text-slate-300",
      )}
      aria-hidden
    >
      {EXECUTION_GLYPH[state]}
    </span>
  );
}

export function Intent({ children, className }: { children: ReactNode; className?: string }) {
  return <p className={cn("text-[13px] leading-snug text-slate-700", className)}>{children}</p>;
}

export function MetaLine({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("text-[11px] tabular-nums text-slate-500", className)}>{children}</div>;
}

export function SectionLabel({ children, right }: { children: ReactNode; right?: ReactNode }) {
  return (
    <div className="mb-2 flex items-baseline justify-between gap-3">
      <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-slate-500">{children}</div>
      {right}
    </div>
  );
}

export function LockNote({ children = "Completed training is historical" }: { children?: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1 text-[11px] text-slate-500" title={String(children)}>
      <span aria-hidden>🔒</span>
      <span className="hidden sm:inline">{children}</span>
    </span>
  );
}

export function GhostButton({
  children,
  onClick,
  disabled,
  tone = "default",
  className,
  title,
}: {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  tone?: "default" | "primary" | "danger";
  className?: string;
  title?: string;
}) {
  return (
    <button
      type="button"
      title={title}
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "rounded-md border border-slate-200 px-2 py-1 text-[11px] transition-colors disabled:cursor-not-allowed disabled:opacity-40",
        tone === "default" && "text-slate-500 hover:bg-slate-50 hover:text-slate-900",
        tone === "primary" && "border-slate-900/30 bg-slate-900/5 text-slate-900 hover:bg-slate-900/10",
        tone === "danger" && "text-slate-500 hover:border-red-300 hover:text-red-600",
        className,
      )}
    >
      {children}
    </button>
  );
}
