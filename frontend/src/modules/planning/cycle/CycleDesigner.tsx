import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  approveCoachReview,
  createCoachReview,
  createMesocycle,
  createMicrocycle,
  createPlanItem,
  deleteMesocycle,
  deleteMicrocycle,
  deletePlanItem,
  generateSystemAnalysis,
  getCoachReview,
  getSystemAnalysis,
  newCoachReviewVersion,
  reorderMesocycles,
  reorderMicrocycles,
  updateCoachReview,
  updateMesocycle,
  updateMicrocycle,
  updatePlan,
  updatePlanItem,
  type CoachReview,
  type PlanItem,
  type SystemAnalysis,
} from "../api";
import {
  buildPlanView,
  formatDay,
  formatRange,
  isItemLocked,
  itemKind,
  itemPlannedLabel,
  parseDate,
  planSummary,
  targetComparison,
  type MesoView,
  type MicroView,
  type PlanView,
} from "../domain";
import { todayIso } from "../../shared/dates";
import { usePlan } from "../usePlan";
import { AnchorConflictCard } from "./AnchorConflictCard";
import { MesocycleDialog, PlaceholderDialog, PlanDatesDialog } from "./CycleDialogs";
import {
  ExecutionDot,
  GhostButton,
  Intent,
  LockNote,
  MetaLine,
  SectionLabel,
  StateDot,
} from "./CyclePrimitives";
import { CycleReviewPanel } from "./CycleReviewPanel";
import { cn } from "@/lib/utils";

export type CycleFocus = { mesoId?: number; microId?: number; itemId?: number };

export function CycleDesigner({
  athleteId,
  planId,
  focus,
  onRequestNewPlan,
}: {
  athleteId: number;
  planId: number;
  focus?: CycleFocus;
  onRequestNewPlan?: () => void;
}) {
  const { plan, loading, error, refresh } = usePlan(planId);
  const [selectedMesoId, setSelectedMesoId] = useState<number | null>(focus?.mesoId ?? null);
  const [expanded, setExpanded] = useState<Record<number, boolean>>(
    focus?.microId ? { [focus.microId]: true } : {},
  );
  const [mutationError, setMutationError] = useState<string | null>(null);

  useEffect(() => {
    if (focus?.mesoId) setSelectedMesoId(focus.mesoId);
    if (focus?.microId) setExpanded((e) => ({ ...e, [focus.microId!]: true }));
  }, [focus?.mesoId, focus?.microId]);

  const view = useMemo(() => (plan ? buildPlanView(plan) : null), [plan]);

  const selected: MesoView | undefined = view
    ? (view.mesos.find((m) => m.meso.id === selectedMesoId) ??
      view.currentMeso ??
      view.mesos[0])
    : undefined;

  const toggle = (id: number) => setExpanded((e) => ({ ...e, [id]: !e[id] }));

  const runMutation = async (fn: () => Promise<{ success: boolean; error?: string }>) => {
    setMutationError(null);
    const result = await fn();
    if (!result.success) {
      setMutationError(result.error ?? "Action failed");
      return false;
    }
    refresh();
    return true;
  };

  if (loading && !plan) {
    return <p className="text-sm text-slate-500">Loading plan…</p>;
  }
  if (error || !plan || !view) {
    return <p className="text-sm text-red-600">{error ?? "Plan not found"}</p>;
  }

  return (
    <div className="mx-auto grid max-w-6xl gap-5">
      {mutationError ? (
        <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-[12px] text-red-700">
          {mutationError}
        </div>
      ) : null}
      <PlanHeader
        view={view}
        athleteId={athleteId}
        onRequestNewPlan={onRequestNewPlan}
        onUpdateDates={async ({ startDate, targetDate }) => {
          await runMutation(() =>
            updatePlan(plan.id, {
              start_date: startDate,
              goal_event_date: targetDate,
            }),
          );
        }}
      />
      <CycleTimeline
        view={view}
        selectedId={selected?.meso.id}
        onSelect={(id) => setSelectedMesoId(id)}
      />
      {selected ? (
        <MesocycleWorkspace
          view={view}
          meso={selected}
          athleteId={athleteId}
          expanded={expanded}
          onToggle={toggle}
          highlightItemId={focus?.itemId}
          runMutation={runMutation}
          refresh={refresh}
        />
      ) : (
        <EmptyPlanState
          view={view}
          runMutation={runMutation}
          planId={plan.id}
        />
      )}
    </div>
  );
}

function PlanHeader({
  view,
  athleteId,
  onRequestNewPlan,
  onUpdateDates,
}: {
  view: PlanView;
  athleteId: number;
  onRequestNewPlan?: () => void;
  onUpdateDates: (v: { startDate: string | null; targetDate: string | null }) => void;
}) {
  const [datesOpen, setDatesOpen] = useState(false);
  const current = view.current;
  const done = view.micros.filter((m) => m.state === "past").length;
  const target = targetComparison(view);

  return (
    <header className="grid gap-3 border-b border-slate-200 pb-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-xl font-semibold tracking-tight text-slate-900">{view.plan.name}</h2>
          <MetaLine className="mt-1">
            {planSummary(view)} · Goal:{" "}
            <span className="text-slate-900">{view.plan.goal ?? "—"}</span>
          </MetaLine>
          {target ? (
            <MetaLine className="mt-0.5">
              <span
                className={
                  view.targetDeltaDays !== undefined && view.targetDeltaDays < 0
                    ? "text-amber-600"
                    : ""
                }
              >
                {target}
              </span>{" "}
              · adjust the architecture if that is not the shape you want
            </MetaLine>
          ) : null}
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            <GhostButton onClick={() => setDatesOpen(true)}>
              {view.startDate ? "Plan dates" : "Set start date"}
            </GhostButton>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            to={`/coach/athletes/${athleteId}/activities`}
            className="rounded-md border border-slate-200 px-2.5 py-1 text-[11px] text-slate-500 hover:text-slate-900"
          >
            View in Calendar →
          </Link>
          {onRequestNewPlan ? (
            <GhostButton onClick={onRequestNewPlan}>+ New training plan</GhostButton>
          ) : null}
        </div>
      </div>

      {view.conflicts.length ? (
        <div className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2">
          <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-amber-700">
            {view.conflicts.length} anchor conflict{view.conflicts.length === 1 ? "" : "s"}
          </span>
          <MetaLine className="mt-0.5">
            Nothing was moved automatically — resolve each one on its block.
          </MetaLine>
        </div>
      ) : null}

      {current && current.startDate && current.endDate ? (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-md border border-slate-900/20 bg-slate-900/5 px-3 py-2">
          <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-slate-900">
            Current position
          </span>
          <span className="text-[13px] font-medium text-slate-900">
            {current.label} of {view.micros.length}
          </span>
          <MetaLine>{formatRange(current.startDate, current.endDate)}</MetaLine>
          <MetaLine>
            {view.currentMeso?.meso.name} · Focus: {current.micro.intent}
          </MetaLine>
        </div>
      ) : null}

      {view.periodCount ? (
        <div className="flex items-center gap-3">
          <div className="h-1.5 flex-1 overflow-hidden rounded bg-slate-100">
            <div
              className="h-full rounded bg-slate-700"
              style={{ width: `${Math.round(view.progress * 100)}%` }}
            />
          </div>
          <MetaLine>
            {done} completed · {view.current ? 1 : 0} current ·{" "}
            {view.micros.length - done - (view.current ? 1 : 0)} upcoming
          </MetaLine>
        </div>
      ) : null}

          <PlanDatesDialog
        open={datesOpen}
        onOpenChange={setDatesOpen}
        {...(view.plan.start_date ? { startDate: view.plan.start_date } : {})}
        {...(view.plan.goal_event_date ? { targetDate: view.plan.goal_event_date } : {})}
        onSubmit={onUpdateDates}
      />
    </header>
  );
}

function CycleTimeline({
  view,
  selectedId,
  onSelect,
}: {
  view: PlanView;
  selectedId?: number;
  onSelect: (id: number) => void;
}) {
  const today = todayIso();
  const todayPct = useMemo(() => {
    if (!view.startDate || !view.endDate) return null;
    const total =
      parseDate(view.endDate).getTime() - parseDate(view.startDate).getTime() + 86400000;
    const at = parseDate(today).getTime() - parseDate(view.startDate).getTime();
    return Math.min(100, Math.max(0, (at / total) * 100));
  }, [view.startDate, view.endDate, today]);

  if (!view.mesos.length) return null;

  return (
    <section>
      <SectionLabel
        right={
          <MetaLine>
            {view.dated ? `Today · ${formatDay(today)}` : "Duration mode · no dates yet"}
          </MetaLine>
        }
      >
        Training architecture
      </SectionLabel>
      <div className="relative">
        <div className="flex items-stretch gap-2">
          {view.mesos.map((m) => (
            <div
              key={m.meso.id}
              className="flex min-w-0 basis-0 items-stretch gap-2"
              style={{ flexGrow: Math.max(1, m.durationDays || 3) }}
            >
              {m.gapBeforeDays ? (
                <div className="flex w-14 shrink-0 flex-col justify-center rounded-lg border border-dashed border-slate-200 bg-slate-50 p-2 text-center">
                  <MetaLine>Unplanned</MetaLine>
                  <MetaLine>{m.gapBeforeDays} days</MetaLine>
                </div>
              ) : null}
              <button
                type="button"
                onClick={() => onSelect(m.meso.id)}
                className={cn(
                  "min-w-0 flex-1 rounded-lg border p-3 text-left transition-colors",
                  m.state === "current" && "border-slate-900/40 bg-slate-900/5",
                  m.state === "past" && "border-slate-200 bg-slate-50",
                  m.state === "future" && "border-dashed border-slate-200 bg-white",
                  m.conflict && "border-amber-400 bg-amber-50",
                  selectedId === m.meso.id && "ring-1 ring-slate-400",
                )}
              >
                <div className="flex items-center gap-1.5">
                  <StateDot state={m.state} />
                  <span className="truncate text-[13px] font-semibold tracking-tight text-slate-900">
                    {m.meso.name}
                  </span>
                </div>
                <Intent className="mt-1 line-clamp-2 text-slate-500">{m.meso.intent}</Intent>
                <MetaLine className="mt-2">{blockMeta(m)}</MetaLine>
                {m.anchorDate ? (
                  <MetaLine className="mt-0.5">⚓ Anchored · {formatDay(m.anchorDate)}</MetaLine>
                ) : null}
                {m.conflict ? (
                  <MetaLine className="mt-0.5 text-amber-700">Anchor conflict</MetaLine>
                ) : null}
              </button>
            </div>
          ))}
        </div>
        {todayPct !== null ? (
          <div className="pointer-events-none absolute -bottom-3 left-0 right-0">
            <div className="relative h-3">
              <div className="absolute -top-1 h-4 w-px bg-slate-900" style={{ left: `${todayPct}%` }} />
              <div
                className="absolute top-1.5 -translate-x-1/2 whitespace-nowrap text-[10px] text-slate-900"
                style={{ left: `${todayPct}%` }}
              >
                today
              </div>
            </div>
          </div>
        ) : null}
      </div>
      <div className="mt-6" />
    </section>
  );
}

function blockMeta(m: MesoView): string {
  if (!m.periodCount) return "No periods yet";
  const structure = `${m.durationDays} days · ${m.periodCount} period${m.periodCount === 1 ? "" : "s"}`;
  return m.startDate && m.endDate ? `${formatRange(m.startDate, m.endDate)} · ${structure}` : structure;
}

function MesocycleWorkspace({
  view,
  meso,
  athleteId,
  expanded,
  onToggle,
  highlightItemId,
  runMutation,
  refresh,
}: {
  view: PlanView;
  meso: MesoView;
  athleteId: number;
  expanded: Record<number, boolean>;
  onToggle: (id: number) => void;
  highlightItemId?: number;
  runMutation: (fn: () => Promise<{ success: boolean; error?: string }>) => Promise<boolean>;
  refresh: () => void;
}) {
  const [analysis, setAnalysis] = useState<SystemAnalysis | null>(null);
  const [review, setReview] = useState<CoachReview | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([getSystemAnalysis(meso.meso.id), getCoachReview(meso.meso.id)]).then(
      ([a, r]) => {
        if (cancelled) return;
        setAnalysis(a.success ? (a.system_analysis ?? null) : null);
        setReview(r.success ? (r.coach_review ?? null) : null);
      },
    );
    return () => {
      cancelled = true;
    };
  }, [meso.meso.id]);

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
      <section className="grid gap-3">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <StateDot state={meso.state} />
                <h3 className="text-[15px] font-semibold tracking-tight text-slate-900">
                  {meso.meso.name}
                </h3>
                {meso.locked ? <LockNote>Historical block</LockNote> : null}
                {meso.anchorDate ? (
                  <span className="rounded border border-slate-200 px-1.5 py-0.5 text-[10px] text-slate-500">
                    ⚓ Anchored · {formatDay(meso.anchorDate)}
                  </span>
                ) : null}
              </div>
              <Intent className="mt-1">{meso.meso.intent}</Intent>
              <MetaLine className="mt-1">{blockMeta(meso)}</MetaLine>
            </div>
            <MesoControls view={view} meso={meso} runMutation={runMutation} />
          </div>

          {meso.conflict ? (
            <AnchorConflictCard
              conflict={meso.conflict}
              onShortenPrevious={async () => {
                const prevBlock = view.mesos[meso.index - 1];
                const lastEditable = [...(prevBlock?.micros ?? [])]
                  .reverse()
                  .find((mc) => !mc.locked);
                if (!lastEditable || !meso.conflict) return;
                await runMutation(() =>
                  updateMicrocycle(lastEditable.micro.id, {
                    duration_days: Math.max(
                      1,
                      lastEditable.micro.duration_days - meso.conflict!.overrun_days,
                    ),
                  }),
                );
              }}
              onMoveAnchor={async () => {
                if (!meso.conflict) return;
                await runMutation(() =>
                  updateMesocycle(meso.meso.id, { anchor_date: meso.conflict!.would_start }),
                );
              }}
              onRemoveAnchor={async () => {
                await runMutation(() => updateMesocycle(meso.meso.id, { anchor_date: null }));
              }}
            />
          ) : null}

          {meso.gapBeforeDays ? (
            <MetaLine className="mt-2">
              Unplanned · {meso.gapBeforeDays} days before this block, created by its anchor.
            </MetaLine>
          ) : null}
        </div>

        <div className="grid gap-2">
          {meso.micros.map((mv) => (
            <MicrocycleCard
              key={mv.micro.id}
              mv={mv}
              view={view}
              athleteId={athleteId}
              open={!!expanded[mv.micro.id] || mv.state === "current"}
              onToggle={() => onToggle(mv.micro.id)}
              highlightItemId={highlightItemId}
              runMutation={runMutation}
            />
          ))}
          {!meso.micros.length ? (
            <div className="rounded-md border border-dashed border-slate-200 p-4 text-[13px] text-slate-500">
              No periods yet — add them when the shape is clear. The block intent is enough for now.
            </div>
          ) : null}
          {meso.state !== "past" ? (
            <AddMicroForm mesoId={meso.meso.id} runMutation={runMutation} />
          ) : null}
        </div>
      </section>

      <aside className="grid content-start gap-3">
        <CycleReviewPanel
          mesoName={meso.meso.name}
          analysis={analysis}
          review={review}
          onGenerateAnalysis={async () => {
            const ok = await runMutation(() => generateSystemAnalysis(meso.meso.id));
            if (ok) {
              const a = await getSystemAnalysis(meso.meso.id);
              if (a.success) setAnalysis(a.system_analysis ?? null);
            }
          }}
          onCreateReview={async ({ fromAnalysis }) => {
            const ok = await runMutation(() =>
              createCoachReview(meso.meso.id, {
                source_analysis_id: fromAnalysis ? analysis?.id : null,
                ...(fromAnalysis
                  ? {}
                  : { content: "What did we learn from this cycle?" }),
              }),
            );
            if (ok) {
              const r = await getCoachReview(meso.meso.id);
              if (r.success) setReview(r.coach_review ?? null);
            }
          }}
          onUpdateReview={async (patch) => {
            if (!review) return;
            setReview({ ...review, ...patch });
            await updateCoachReview(review.id, patch);
          }}
          onApprove={async () => {
            if (!review) return;
            const ok = await runMutation(() => approveCoachReview(review.id));
            if (ok) {
              const r = await getCoachReview(meso.meso.id);
              if (r.success) setReview(r.coach_review ?? null);
              refresh();
            }
          }}
          onNewVersion={async () => {
            if (!review) return;
            const ok = await runMutation(() => newCoachReviewVersion(review.id));
            if (ok) {
              const r = await getCoachReview(meso.meso.id);
              if (r.success) setReview(r.coach_review ?? null);
            }
          }}
        />
        <div className="rounded-lg border border-dashed border-slate-200 p-3">
          <SectionLabel>Legend</SectionLabel>
          <ul className="grid gap-1 text-[11px] text-slate-500">
            <li>✓ completed · ⚠ execution issue · ✕ missed</li>
            <li>● current · ○ upcoming</li>
            <li>Dashed = placeholder (intent only, not yet a workout)</li>
            <li>⚓ = anchored to a fixed start date</li>
            <li>🔒 = historical or executed, cannot be changed</li>
          </ul>
        </div>
      </aside>
    </div>
  );
}

function MesoControls({
  view,
  meso,
  runMutation,
}: {
  view: PlanView;
  meso: MesoView;
  runMutation: (fn: () => Promise<{ success: boolean; error?: string }>) => Promise<boolean>;
}) {
  const [editOpen, setEditOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const canAnchor = view.dated && meso.state !== "past";

  const moveMeso = async (direction: -1 | 1) => {
    const ids = view.mesos.map((m) => m.meso.id);
    const idx = ids.indexOf(meso.meso.id);
    const swap = idx + direction;
    if (swap < 0 || swap >= ids.length) return;
    const next = [...ids];
    const tmp = next[idx]!;
    next[idx] = next[swap]!;
    next[swap] = tmp;
    await runMutation(() => reorderMesocycles(view.plan.id, next));
  };

  return (
    <div className="grid gap-2">
      <div className="flex flex-wrap gap-1.5">
        {!meso.locked ? (
          <>
            <GhostButton onClick={() => moveMeso(-1)} title="Move earlier">
              ↑
            </GhostButton>
            <GhostButton onClick={() => moveMeso(1)} title="Move later">
              ↓
            </GhostButton>
          </>
        ) : (
          <MetaLine>Structure locked</MetaLine>
        )}
        <GhostButton onClick={() => setEditOpen(true)}>Edit block</GhostButton>
        {meso.anchorDate ? (
          <GhostButton
            onClick={() =>
              runMutation(() => updateMesocycle(meso.meso.id, { anchor_date: null }))
            }
          >
            Remove anchor
          </GhostButton>
        ) : null}
        {!meso.locked ? (
          <GhostButton
            tone="danger"
            onClick={() => runMutation(() => deleteMesocycle(meso.meso.id))}
          >
            Remove
          </GhostButton>
        ) : null}
        <GhostButton tone="primary" onClick={() => setCreateOpen(true)}>
          + Block
        </GhostButton>
      </div>

      <MesocycleDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        mode="edit"
        canAnchor={canAnchor}
        initial={{
          name: meso.meso.name,
          intent: meso.meso.intent ?? "",
          ...(meso.meso.anchor_date ? { anchorDate: meso.meso.anchor_date } : {}),
        }}
        onSubmit={({ name, intent, anchorDate }) => {
          void runMutation(() =>
            updateMesocycle(meso.meso.id, {
              name,
              intent,
              ...(canAnchor ? { anchor_date: anchorDate } : {}),
            }),
          );
        }}
      />
      <MesocycleDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        mode="create"
        canAnchor={view.dated}
        onSubmit={({ name, intent, anchorDate }) => {
          void runMutation(() =>
            createMesocycle(view.plan.id, {
              name,
              intent,
              ...(anchorDate ? { anchor_date: anchorDate } : {}),
            }),
          );
        }}
      />
    </div>
  );
}

function MicrocycleCard({
  mv,
  view,
  athleteId,
  open,
  onToggle,
  highlightItemId,
  runMutation,
}: {
  mv: MicroView;
  view: PlanView;
  athleteId: number;
  open: boolean;
  onToggle: () => void;
  highlightItemId?: number;
  runMutation: (fn: () => Promise<{ success: boolean; error?: string }>) => Promise<boolean>;
}) {
  const navigate = useNavigate();
  const [editing, setEditing] = useState(false);
  const items = [...(mv.micro.items ?? [])].sort((a, b) => a.ordinal - b.ordinal);
  const range = mv.startDate && mv.endDate ? formatRange(mv.startDate, mv.endDate) : null;

  const openBuilderForNewItem = async () => {
    const result = await createPlanItem(mv.micro.id, {
      title: "New workout",
      intent: mv.micro.intent,
    });
    if (!result.success || !result.item) return;
    navigate(
      `/planning/workout/new?athleteId=${athleteId}&planItemId=${result.item.id}&planId=${view.plan.id}&mesoId=${mv.mesoId}&microId=${mv.micro.id}`,
    );
  };

  const moveMicro = async (direction: -1 | 1) => {
    const meso = view.mesos.find((m) => m.meso.id === mv.mesoId);
    if (!meso) return;
    const ids = meso.micros.map((m) => m.micro.id);
    const idx = ids.indexOf(mv.micro.id);
    const swap = idx + direction;
    if (swap < 0 || swap >= ids.length) return;
    const next = [...ids];
    const tmp = next[idx]!;
    next[idx] = next[swap]!;
    next[swap] = tmp;
    await runMutation(() => reorderMicrocycles(mv.mesoId, next));
  };

  return (
    <article
      className={cn(
        "rounded-lg border bg-white",
        mv.state === "current" && "border-slate-900/40 bg-slate-900/5",
        mv.state === "past" && "border-slate-200 bg-slate-50/60",
        mv.state === "future" && "border-slate-200",
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-2 p-3">
        <button type="button" onClick={onToggle} className="min-w-0 flex-1 text-left">
          <div className="flex items-center gap-1.5">
            <StateDot state={mv.state} />
            <span className="text-[13px] font-semibold tracking-tight text-slate-900">
              {mv.label}
            </span>
            <span className="rounded border border-slate-200 px-1.5 py-0.5 text-[10px] text-slate-500">
              {mv.micro.duration_days} days
            </span>
            {mv.locked ? (
              <LockNote>
                {mv.lockReason === "executed"
                  ? "Contains executed training"
                  : "Historical period"}
              </LockNote>
            ) : null}
            <span className="ml-auto text-[11px] text-slate-500">{open ? "−" : "+"}</span>
          </div>
          <Intent className="mt-1">{mv.micro.intent}</Intent>
          <MetaLine className="mt-1">
            {range ? `${range} · ` : ""}
            {items.length} item{items.length === 1 ? "" : "s"}
          </MetaLine>
        </button>
        <div className="flex flex-wrap gap-1.5">
          <Link
            to={`/coach/athletes/${athleteId}/activities`}
            className="rounded-md border border-slate-200 px-2 py-1 text-[11px] text-slate-500 hover:text-slate-900"
          >
            View in Calendar
          </Link>
          {!mv.locked ? (
            <>
              <GhostButton onClick={() => moveMicro(-1)}>↑</GhostButton>
              <GhostButton onClick={() => moveMicro(1)}>↓</GhostButton>
              <GhostButton onClick={() => setEditing((v) => !v)}>Edit period</GhostButton>
              <GhostButton
                tone="danger"
                onClick={() => runMutation(() => deleteMicrocycle(mv.micro.id))}
              >
                Remove
              </GhostButton>
            </>
          ) : null}
        </div>
      </div>

      {editing && !mv.locked ? (
        <MicroEditor mv={mv} onDone={() => setEditing(false)} runMutation={runMutation} />
      ) : null}

      {open ? (
        <div className="border-t border-slate-200 p-3">
          <div className="grid gap-1.5">
            {items.map((item) => (
              <PlanItemRow
                key={item.id}
                item={item}
                mv={mv}
                athleteId={athleteId}
                planId={view.plan.id}
                highlighted={item.id === highlightItemId}
                runMutation={runMutation}
              />
            ))}
            {!items.length ? (
              <p className="rounded-md border border-dashed border-slate-200 p-3 text-[12px] text-slate-500">
                No sessions defined yet — the intent is enough for now.
              </p>
            ) : null}
          </div>

          {!mv.locked ? (
            <div className="mt-2 flex flex-wrap items-center gap-1.5">
              <GhostButton
                onClick={() =>
                  runMutation(() =>
                    createPlanItem(mv.micro.id, { title: "New session intent" }),
                  )
                }
              >
                + Add placeholder
              </GhostButton>
              <GhostButton tone="primary" onClick={openBuilderForNewItem}>
                + Add workout
              </GhostButton>
              <GhostButton onClick={openBuilderForNewItem}>
                Open builder with this context →
              </GhostButton>
            </div>
          ) : (
            <MetaLine className="mt-2">
              {mv.lockReason === "executed"
                ? "Contains executed training · structure is locked"
                : "Historical period · execution is locked"}
            </MetaLine>
          )}

          <div className="mt-2 rounded-md border border-dashed border-slate-200 bg-slate-50 p-2">
            <MetaLine>
              Context passed to the builder: {view.plan.name} ·{" "}
              {view.mesos.find((m) => m.meso.id === mv.mesoId)?.meso.name} · {mv.label}
              {range ? ` · ${range}` : ""} · Focus: {mv.micro.intent}
            </MetaLine>
          </div>
        </div>
      ) : null}
    </article>
  );
}

function MicroEditor({
  mv,
  onDone,
  runMutation,
}: {
  mv: MicroView;
  onDone: () => void;
  runMutation: (fn: () => Promise<{ success: boolean; error?: string }>) => Promise<boolean>;
}) {
  const [name, setName] = useState(mv.micro.name ?? "");
  const [intent, setIntent] = useState(mv.micro.intent ?? "");
  const [days, setDays] = useState(mv.micro.duration_days);

  return (
    <div className="grid gap-2 border-t border-slate-200 p-3">
      <div className="grid gap-1.5 sm:grid-cols-2">
        <label className="grid gap-1">
          <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-slate-500">
            Custom name (optional)
          </span>
          <input
            value={name}
            placeholder="e.g. Recovery Block"
            onChange={(e) => setName(e.target.value)}
            className="rounded border border-slate-200 bg-white px-2 py-1 text-[12px] outline-none focus:border-slate-400"
          />
        </label>
        <label className="grid gap-1">
          <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-slate-500">
            Duration (days)
          </span>
          <div className="flex items-center gap-1.5">
            <input
              type="number"
              min={1}
              max={28}
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="w-20 rounded border border-slate-200 bg-white px-2 py-1 text-[12px] outline-none focus:border-slate-400"
            />
            <GhostButton onClick={() => setDays(7)}>7 days</GhostButton>
            <GhostButton onClick={() => setDays(5)}>5</GhostButton>
            <GhostButton onClick={() => setDays(10)}>10</GhostButton>
          </div>
        </label>
      </div>
      <label className="grid gap-1">
        <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-slate-500">
          Intent
        </span>
        <input
          value={intent}
          onChange={(e) => setIntent(e.target.value)}
          className="rounded border border-slate-200 bg-white px-2 py-1 text-[12px] outline-none focus:border-slate-400"
        />
      </label>
      <MetaLine>
        End date is derived. Changing this duration reflows later unanchored periods only.
      </MetaLine>
      <div className="flex flex-wrap gap-1.5">
        <GhostButton
          tone="primary"
          onClick={async () => {
            await runMutation(() =>
              updateMicrocycle(mv.micro.id, {
                name: name || null,
                intent,
                duration_days: days,
              }),
            );
            onDone();
          }}
        >
          Save
        </GhostButton>
        <GhostButton onClick={onDone}>Cancel</GhostButton>
      </div>
    </div>
  );
}

function PlanItemRow({
  item,
  mv,
  athleteId,
  planId,
  highlighted,
  runMutation,
}: {
  item: PlanItem;
  mv: MicroView;
  athleteId: number;
  planId: number;
  highlighted?: boolean;
  runMutation: (fn: () => Promise<{ success: boolean; error?: string }>) => Promise<boolean>;
}) {
  if (itemKind(item) === "placeholder") {
    return (
      <PlaceholderRow
        item={item}
        mv={mv}
        athleteId={athleteId}
        planId={planId}
        highlighted={highlighted}
        runMutation={runMutation}
      />
    );
  }

  const locked = isItemLocked(item, mv.state, mv.micro.lock_state);

  return (
    <div
      className={cn(
        "flex flex-wrap items-center justify-between gap-2 rounded-md border border-slate-200 bg-white p-2.5",
        highlighted && "border-slate-400 ring-1 ring-slate-400",
      )}
    >
      <div className="flex min-w-0 items-center gap-1.5">
        <ExecutionDot state="planned" />
        <span className="text-[13px] font-medium text-slate-900">{item.title}</span>
        <MetaLine>{itemPlannedLabel(item)}</MetaLine>
        {highlighted ? <MetaLine className="text-slate-900">just added</MetaLine> : null}
      </div>
      <div className="flex items-center gap-1.5">
        {locked ? (
          <LockNote />
        ) : (
          <>
            {item.workout_id ? (
              <Link
                to={`/planning/workout/${item.workout_id}`}
                className="rounded-md border border-slate-200 px-2 py-1 text-[11px] text-slate-500 hover:text-slate-900"
              >
                Edit steps
              </Link>
            ) : null}
            <GhostButton
              tone="danger"
              onClick={() => runMutation(() => deletePlanItem(item.id))}
            >
              Remove
            </GhostButton>
          </>
        )}
      </div>
    </div>
  );
}

function PlaceholderRow({
  item,
  mv,
  athleteId,
  planId,
  highlighted,
  runMutation,
}: {
  item: PlanItem;
  mv: MicroView;
  athleteId: number;
  planId: number;
  highlighted?: boolean;
  runMutation: (fn: () => Promise<{ success: boolean; error?: string }>) => Promise<boolean>;
}) {
  const [editOpen, setEditOpen] = useState(false);
  const locked = isItemLocked(item, mv.state, mv.micro.lock_state);

  return (
    <>
      <div
        className={cn(
          "rounded-md border border-dashed border-slate-200 bg-slate-50/40 p-2.5",
          highlighted && "ring-1 ring-slate-400",
        )}
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] text-slate-400" aria-hidden>
                ○
              </span>
              <span className="text-[13px] text-slate-700">{item.title}</span>
              <span className="rounded border border-dashed border-slate-200 px-1.5 py-0.5 text-[10px] text-slate-500">
                placeholder
              </span>
            </div>
            {item.intent ? <MetaLine className="mt-0.5">{item.intent}</MetaLine> : null}
          </div>
          {!locked ? (
            <div className="flex gap-1.5">
              <GhostButton onClick={() => setEditOpen(true)}>Edit</GhostButton>
              <Link
                to={`/planning/workout/new?athleteId=${athleteId}&planItemId=${item.id}&planId=${planId}&mesoId=${mv.mesoId}&microId=${mv.micro.id}`}
                className="rounded-md border border-slate-900/30 bg-slate-900/5 px-2 py-1 text-[11px] text-slate-900 hover:bg-slate-900/10"
              >
                Convert to workout →
              </Link>
              <GhostButton
                tone="danger"
                onClick={() => runMutation(() => deletePlanItem(item.id))}
              >
                Remove
              </GhostButton>
            </div>
          ) : (
            <LockNote />
          )}
        </div>
      </div>

      <PlaceholderDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        initial={{ title: item.title, intent: item.intent }}
        onSubmit={({ title, intent }) => {
          void runMutation(() => updatePlanItem(item.id, { title, intent }));
        }}
      />
    </>
  );
}

function AddMicroForm({
  mesoId,
  runMutation,
}: {
  mesoId: number;
  runMutation: (fn: () => Promise<{ success: boolean; error?: string }>) => Promise<boolean>;
}) {
  const [intent, setIntent] = useState("");
  const [days, setDays] = useState(7);
  const [name, setName] = useState("");

  return (
    <div className="grid gap-1.5 rounded-md border border-dashed border-slate-200 p-3 sm:grid-cols-[1fr_auto_auto_auto]">
      <input
        value={intent}
        onChange={(e) => setIntent(e.target.value)}
        placeholder="New training period — what is its intent?"
        className="rounded border border-slate-200 bg-white px-2 py-1 text-[12px] outline-none focus:border-slate-400"
      />
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Custom name"
        className="w-36 rounded border border-slate-200 bg-white px-2 py-1 text-[12px] outline-none focus:border-slate-400"
      />
      <input
        type="number"
        min={1}
        max={28}
        value={days}
        onChange={(e) => setDays(Number(e.target.value))}
        className="w-20 rounded border border-slate-200 bg-white px-2 py-1 text-[12px] outline-none focus:border-slate-400"
      />
      <GhostButton
        tone="primary"
        onClick={async () => {
          await runMutation(() =>
            createMicrocycle(mesoId, {
              intent: intent || "Describe the intent of this period",
              duration_days: days,
              ...(name ? { name } : {}),
            }),
          );
          setIntent("");
          setName("");
          setDays(7);
        }}
      >
        + Add period
      </GhostButton>
    </div>
  );
}

function EmptyPlanState({
  view,
  planId,
  runMutation,
}: {
  view: PlanView;
  planId: number;
  runMutation: (fn: () => Promise<{ success: boolean; error?: string }>) => Promise<boolean>;
}) {
  const [createOpen, setCreateOpen] = useState(false);
  return (
    <div className="rounded-lg border border-dashed border-slate-200 p-6 text-center">
      <p className="text-[13px] text-slate-500">
        An empty macrocycle. Start with structure — blocks first, detail later.
      </p>
      <MetaLine className="mt-1">{planSummary(view)}</MetaLine>
      <div className="mt-3 flex justify-center gap-2">
        <GhostButton tone="primary" onClick={() => setCreateOpen(true)}>
          + Add first block
        </GhostButton>
      </div>
      <MesocycleDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        mode="create"
        canAnchor={view.dated}
        onSubmit={({ name, intent, anchorDate }) => {
          void runMutation(() =>
            createMesocycle(planId, {
              name,
              intent,
              ...(anchorDate ? { anchor_date: anchorDate } : {}),
            }),
          );
        }}
      />
    </div>
  );
}
