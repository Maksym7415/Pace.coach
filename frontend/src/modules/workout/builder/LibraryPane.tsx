import { useEffect, useState } from "react";
import { listWorkoutTemplates, type WorkoutTemplate as SavedTemplate } from "../../training/api";
import { templatesForSport } from "../templates";
import type { WorkoutTemplate as BuiltinTemplate, StepType } from "../types";
import { stepTypesForSport } from "../types";

type LibraryPaneProps = {
  sportCode: string | null;
  onAddStep: (type: StepType) => void;
  onAddRepeat: () => void;
  onApplyBuiltin: (template: BuiltinTemplate) => void;
  onApplySaved: (template: SavedTemplate) => void;
};

type Tab = "blocks" | "templates";

export function LibraryPane({
  sportCode,
  onAddStep,
  onAddRepeat,
  onApplyBuiltin,
  onApplySaved,
}: LibraryPaneProps) {
  const [tab, setTab] = useState<Tab>("blocks");
  const [saved, setSaved] = useState<SavedTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const types = stepTypesForSport(sportCode);
  const builtins = templatesForSport(sportCode);

  useEffect(() => {
    if (tab !== "templates") return;
    setLoading(true);
    listWorkoutTemplates().then((result) => {
      setSaved(result.success ? (result.templates ?? []) : []);
      setLoading(false);
    });
  }, [tab]);

  const filteredSaved = sportCode
    ? saved.filter((t) => t.sport_code === sportCode)
    : saved;

  return (
    <div className="builder-pane builder-library card stack">
      <div className="row-between">
        <h3>Library</h3>
        <span className="muted">drag → canvas</span>
      </div>
      <div className="builder-library-tabs">
        <button
          type="button"
          className={tab === "blocks" ? "" : "secondary"}
          onClick={() => setTab("blocks")}
        >
          Blocks
        </button>
        <button
          type="button"
          className={tab === "templates" ? "" : "secondary"}
          onClick={() => setTab("templates")}
        >
          Templates
        </button>
      </div>

      {tab === "blocks" ? (
        <div className="stack">
          {types.map((t) => (
            <button
              key={t.value}
              type="button"
              className="secondary builder-library-item"
              onClick={() => onAddStep(t.value)}
            >
              + {t.label}
            </button>
          ))}
          <button type="button" className="secondary builder-library-item" onClick={onAddRepeat}>
            + Repeat block
          </button>
        </div>
      ) : (
        <div className="stack">
          {loading && <p className="muted">Loading templates…</p>}
          {builtins.length > 0 && (
            <>
              <p className="muted builder-library-group">Built-in</p>
              {builtins.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  className="secondary builder-library-item"
                  onClick={() => onApplyBuiltin(t)}
                >
                  {t.label}
                </button>
              ))}
            </>
          )}
          <p className="muted builder-library-group">Saved</p>
          {filteredSaved.length === 0 && !loading ? (
            <p className="muted">No saved templates yet.</p>
          ) : (
            filteredSaved.map((t) => (
              <button
                key={t.id}
                type="button"
                className="secondary builder-library-item"
                onClick={() => onApplySaved(t)}
              >
                {t.title}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
