import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function PageFrame({
  title,
  question,
  children,
  showTitle = false,
}: {
  title: string;
  question: string;
  children: ReactNode;
  /** Shell header already shows phase/label/question — keep off by default. */
  showTitle?: boolean;
}) {
  return (
    <div className="mx-auto max-w-6xl space-y-3">
      {showTitle ? (
        <div className="mb-1">
          <h1 className="text-lg font-semibold tracking-tight text-slate-900">{title}</h1>
          <p className="text-sm text-slate-500">{question}</p>
        </div>
      ) : null}
      <div className="grid gap-3">{children}</div>
    </div>
  );
}

export function SectionBox({
  label,
  note,
  className,
  children,
}: {
  label: string;
  note?: string;
  className?: string;
  children?: ReactNode;
}) {
  return (
    <section className={cn("rounded-md border border-slate-200 bg-white p-3 shadow-sm", className)}>
      <div className="mb-2 flex items-baseline justify-between gap-2">
        <div className="font-mono text-[11px] uppercase tracking-wider text-slate-600">{label}</div>
        {note ? <div className="text-[11px] text-slate-400">{note}</div> : null}
      </div>
      {children}
    </section>
  );
}

export function SectionRow({
  children,
  cols = 2,
  className,
}: {
  children: ReactNode;
  cols?: 2 | 3 | 4;
  className?: string;
}) {
  const grid =
    cols === 2 ? "md:grid-cols-2" : cols === 3 ? "md:grid-cols-3" : "md:grid-cols-4";
  return <div className={cn("grid gap-3", grid, className)}>{children}</div>;
}

export function Chip({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded border border-slate-200 bg-slate-50 px-2 py-1 text-[11px] text-slate-600",
        className,
      )}
    >
      {children}
    </span>
  );
}

export function MetricBar({ label, value, max = 100 }: { label: string; value: number | null; max?: number }) {
  const pct =
    value == null || max <= 0 ? 0 : Math.max(0, Math.min(100, Math.round((value / max) * 100)));
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 shrink-0 text-[11px] text-slate-500">{label}</div>
      <div className="h-2 flex-1 rounded bg-slate-100">
        <div className="h-2 rounded bg-slate-400" style={{ width: `${pct}%` }} />
      </div>
      <div className="w-10 text-right text-[11px] text-slate-500">{value ?? "—"}</div>
    </div>
  );
}
