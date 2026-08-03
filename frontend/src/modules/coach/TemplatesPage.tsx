import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import {
  deleteWorkoutTemplate,
  listWorkoutTemplates,
  type WorkoutTemplate,
} from "../training/api";
import { WORKOUT_TEMPLATES } from "../workout/templates";
import { PageFrame, SectionBox } from "../shared/PageChrome";

export function TemplatesPage() {
  const [templates, setTemplates] = useState<WorkoutTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function refresh() {
    setLoading(true);
    listWorkoutTemplates().then((result) => {
      if (!result.success) {
        setError(result.error ?? "Failed to load templates");
        setTemplates([]);
      } else {
        setError(null);
        setTemplates(result.templates ?? []);
      }
      setLoading(false);
    });
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleDelete(template: WorkoutTemplate) {
    if (!window.confirm(`Delete template "${template.title}"?`)) return;
    const result = await deleteWorkoutTemplate(template.id);
    if (!result.success) {
      setError(result.error ?? "Failed to delete template");
      return;
    }
    setTemplates((prev) => prev.filter((t) => t.id !== template.id));
  }

  return (
    <PageFrame title="Templates" question="Reusable building blocks">
      <SectionBox label="Templates" note="Reusable building blocks for planning">
        <div className="row-between" style={{ gap: "0.5rem", flexWrap: "wrap" }}>
          <Link to="/templates/new">
            <button type="button">Create template</button>
          </Link>
          <Link to="/planning/workout/new">
            <button type="button" className="secondary">
              Open builder
            </button>
          </Link>
        </div>
        {error && <p className="error">{error}</p>}
      </SectionBox>

      <SectionBox label="Saved templates" note="Yours">
        {loading && <p className="muted">Loading…</p>}
        {!loading && templates.length === 0 && (
          <p className="muted">No saved templates yet.</p>
        )}
        <div className="stack">
          {templates.map((t) => (
            <div key={t.id} className="card stack">
              <div className="row-between" style={{ gap: "0.75rem", flexWrap: "wrap" }}>
                <div>
                  <strong>{t.title}</strong>
                  <p className="muted">
                    {t.sport_name ?? t.sport_code} · {t.workout_type}
                    {t.purpose ? ` · ${t.purpose}` : ""}
                  </p>
                </div>
                <div className="step-actions">
                  <Link to={`/planning/workout/new?templateId=${t.id}`}>
                    <button type="button" className="secondary">
                      Open in builder
                    </button>
                  </Link>
                  <Link to={`/templates/${t.id}/edit`}>
                    <button type="button" className="secondary">
                      Edit
                    </button>
                  </Link>
                  <button type="button" className="secondary" onClick={() => handleDelete(t)}>
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </SectionBox>

      <SectionBox label="Built-in starters" note="Seed structures — open in builder to customize">
        <div className="stack">
          {WORKOUT_TEMPLATES.map((t) => (
            <div key={t.id} className="row-between" style={{ gap: "0.75rem" }}>
              <div>
                <strong>{t.label}</strong>
                <p className="muted">
                  {t.sportCode} · {t.workoutType}
                </p>
              </div>
              <Link to="/planning/workout/new">
                <button type="button" className="secondary">
                  Open builder
                </button>
              </Link>
            </div>
          ))}
        </div>
      </SectionBox>
    </PageFrame>
  );
}
