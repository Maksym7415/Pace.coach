import { Link } from "react-router-dom";
import {
  formatMaybeRange,
  itemKind,
  itemPlannedLabel,
  planSummary,
  type PlanView,
} from "../domain";
import type { TrainingPlan } from "../api";
import { Intent, MetaLine, SectionLabel, StateDot } from "./CyclePrimitives";
import { cn } from "@/lib/utils";

/**
 * Athlete view — four questions:
 * Where am I now? · What are we developing? · Where are we going? · What did we learn?
 */
export function AthleteCycleView({
  plan,
  view,
  calendarHref = "/activities",
}: {
  plan: TrainingPlan;
  view: PlanView;
  calendarHref?: string;
}) {
  const current = view.current;
  const currentMeso = view.currentMeso;
  const nextMeso = view.nextMeso;

  const reviewed = [...view.mesos]
    .filter((m) => m.state === "past")
    .reverse()
    .map((m) => ({
      m,
      review:
        m.meso.coach_review?.status === "approved" ? m.meso.coach_review : null,
    }))
    .find((x) => x.review);

  return (
    <div className="grid gap-5">
      <header className="border-b border-slate-200 pb-4">
        <h2 className="text-xl font-semibold tracking-tight text-slate-900">{plan.name}</h2>
        <MetaLine className="mt-1">
          {planSummary(view)} · Goal:{" "}
          <span className="text-slate-900">{plan.goal ?? "—"}</span>
        </MetaLine>
      </header>

      <section>
        <SectionLabel
          right={<MetaLine>{Math.round(view.progress * 100)}% through the cycle</MetaLine>}
        >
          Where am I now
        </SectionLabel>
        {current ? (
          <div className="rounded-lg border border-slate-900/30 bg-slate-900/5 p-4">
            <div className="text-[15px] font-semibold tracking-tight text-slate-900">
              {current.label} of {view.micros.length}
            </div>
            <MetaLine className="mt-0.5">
              {formatMaybeRange(current.startDate, current.endDate) ??
                `${current.micro.duration_days} days`}{" "}
              · {currentMeso?.meso.name}
            </MetaLine>
          </div>
        ) : (
          <div className="rounded-lg border border-slate-200 p-4 text-[13px] text-slate-500">
            Between training periods.
          </div>
        )}
        <div className="mt-3 flex gap-2">
          {view.mesos.map((m) => (
            <div
              key={m.meso.id}
              style={{ flexGrow: Math.max(1, m.durationDays) }}
              className={cn(
                "min-w-0 basis-0 rounded-md border p-2",
                m.state === "current" && "border-slate-900/40 bg-slate-900/5",
                m.state === "past" && "border-slate-200 bg-slate-50",
                m.state === "future" && "border-dashed border-slate-200",
              )}
            >
              <div className="flex items-center gap-1.5">
                <StateDot state={m.state} />
                <span className="truncate text-[12px] font-medium text-slate-900">
                  {m.meso.name}
                </span>
              </div>
              <MetaLine className="mt-0.5">
                {formatMaybeRange(m.startDate, m.endDate) ??
                  (m.periodCount ? `${m.durationDays} days` : "no periods yet")}
              </MetaLine>
            </div>
          ))}
        </div>
      </section>

      <section>
        <SectionLabel>What are we developing</SectionLabel>
        <div className="grid gap-2 md:grid-cols-2">
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <MetaLine>Current block</MetaLine>
            <div className="mt-0.5 text-[14px] font-semibold tracking-tight text-slate-900">
              {currentMeso?.meso.name ?? "—"}
            </div>
            <Intent className="mt-1">{currentMeso?.meso.intent}</Intent>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <MetaLine>This training period</MetaLine>
            <div className="mt-0.5 text-[14px] font-semibold tracking-tight text-slate-900">
              {current?.label ?? "—"}
              {current && current.micro.duration_days !== 7
                ? ` · ${current.micro.duration_days} days`
                : ""}
            </div>
            <Intent className="mt-1">{current?.micro.intent}</Intent>
          </div>
        </div>
        {current?.micro.items?.length ? (
          <div className="mt-2 grid gap-1.5">
            {[...current.micro.items]
              .sort((a, b) => a.ordinal - b.ordinal)
              .map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between gap-2 rounded-md border border-slate-200 bg-slate-50/60 p-2.5"
                >
                  <div className="flex min-w-0 items-center gap-1.5">
                    <span className="text-[11px] text-slate-400" aria-hidden>
                      ○
                    </span>
                    <span className="text-[13px] text-slate-800">{item.title}</span>
                    <MetaLine>
                      {itemKind(item) === "placeholder"
                        ? "planned focus"
                        : itemPlannedLabel(item)}
                    </MetaLine>
                  </div>
                </div>
              ))}
          </div>
        ) : null}
      </section>

      <section>
        <SectionLabel>Where are we going</SectionLabel>
        {nextMeso ? (
          <div className="rounded-lg border border-dashed border-slate-200 p-4">
            <div className="text-[14px] font-semibold tracking-tight text-slate-900">
              {nextMeso.meso.name}
            </div>
            <Intent className="mt-1">{nextMeso.meso.intent}</Intent>
            <MetaLine className="mt-1">
              {nextMeso.periodCount
                ? `${formatMaybeRange(nextMeso.startDate, nextMeso.endDate) ?? ""}${
                    formatMaybeRange(nextMeso.startDate, nextMeso.endDate) ? " · " : ""
                  }${nextMeso.durationDays} days`
                : "Shape still to be defined"}
            </MetaLine>
          </div>
        ) : (
          <div className="rounded-lg border border-dashed border-slate-200 p-4 text-[13px] text-slate-500">
            Final block of this cycle.
          </div>
        )}
      </section>

      {reviewed?.review ? (
        <section>
          <SectionLabel>What did we learn</SectionLabel>
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <MetaLine>
              {reviewed.m.meso.name} · completed
              {reviewed.review.approved_at ? ` · reviewed ${reviewed.review.approved_at}` : ""}
            </MetaLine>
            <div className="mt-1 font-mono text-[10px] uppercase tracking-[0.14em] text-slate-500">
              Coach&apos;s review
            </div>
            <p className="mt-1 text-[13px] leading-relaxed text-slate-700">
              {reviewed.review.content}
            </p>
            {reviewed.review.next_cycle_focus ? (
              <div className="mt-3 rounded-md border border-slate-200 bg-slate-50 p-2">
                <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-slate-500">
                  Next focus
                </div>
                <p className="mt-0.5 text-[13px] text-slate-700">
                  {reviewed.review.next_cycle_focus}
                </p>
              </div>
            ) : null}
          </div>
        </section>
      ) : null}

      <div>
        <Link
          to={calendarHref}
          className="rounded-md border border-slate-200 px-2.5 py-1 text-[11px] text-slate-500 hover:text-slate-900"
        >
          View in Calendar →
        </Link>
      </div>
    </div>
  );
}
