import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { listWorkoutTemplates, type WorkoutTemplate } from "../training/api";
import { PageFrame, SectionBox } from "../shared/PageChrome";

export function PlanningHubPage() {
  const [templates, setTemplates] = useState<WorkoutTemplate[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listWorkoutTemplates().then((result) => {
      setTemplates(result.success ? (result.templates ?? []).slice(0, 6) : []);
      setLoading(false);
    });
  }, []);

  return (
    <PageFrame title="Planning" question="What should happen next?">
      <SectionBox label="Workout builder" note="Design intent, then structure and assign">
        <p className="muted">
          Build structured workouts, save reusable templates, and assign to one or more athletes.
        </p>
        <div className="row-between" style={{ gap: "0.5rem", flexWrap: "wrap", marginTop: "0.75rem" }}>
          <Link to="/planning/workout/new">
            <button type="button">New workout</button>
          </Link>
          <Link to="/templates">
            <button type="button" className="secondary">
              Browse templates
            </button>
          </Link>
        </div>
      </SectionBox>

      <SectionBox label="Recent templates" note="Quick start from a saved structure">
        {loading && <p className="muted">Loading…</p>}
        {!loading && templates.length === 0 && (
          <p className="muted">
            No saved templates yet.{" "}
            <Link to="/templates/new">Create one</Link> or save from the builder.
          </p>
        )}
        <div className="stack">
          {templates.map((t) => (
            <div key={t.id} className="row-between" style={{ gap: "0.75rem" }}>
              <div>
                <strong>{t.title}</strong>
                <p className="muted">
                  {t.sport_name ?? t.sport_code}
                  {t.purpose ? ` · ${t.purpose}` : ""}
                  {t.duration_min != null ? ` · ${t.duration_min} min` : ""}
                </p>
              </div>
              <Link to={`/planning/workout/new?templateId=${t.id}`}>
                <button type="button" className="secondary">
                  Use
                </button>
              </Link>
            </div>
          ))}
        </div>
      </SectionBox>
    </PageFrame>
  );
}
