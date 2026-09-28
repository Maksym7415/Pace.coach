import { formatDay, type MesoView } from "../domain";
import { GhostButton, MetaLine } from "./CyclePrimitives";

export function AnchorConflictCard({
  conflict,
  onShortenPrevious,
  onMoveAnchor,
  onRemoveAnchor,
}: {
  conflict: NonNullable<MesoView["conflict"]>;
  onShortenPrevious: () => void;
  onMoveAnchor: () => void;
  onRemoveAnchor: () => void;
}) {
  return (
    <div className="mt-3 rounded-md border border-amber-300 bg-amber-50 p-3">
      <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-amber-700">
        Anchor conflict
      </div>
      <p className="mt-1 text-[12px] text-slate-800">{conflict.message}</p>
      <MetaLine className="mt-1">Nothing was moved. Choose how to resolve it:</MetaLine>
      <div className="mt-2 flex flex-wrap gap-1.5">
        <GhostButton onClick={onShortenPrevious}>Shorten previous block</GhostButton>
        <GhostButton onClick={onMoveAnchor}>
          Move anchor to {formatDay(conflict.would_start)}
        </GhostButton>
        <GhostButton onClick={onRemoveAnchor}>Remove anchor</GhostButton>
      </div>
    </div>
  );
}
