import { listAthletes, type CoachAthleteListItem } from "../../coaching/api";
import { todayIso } from "../../shared/dates";
import { useEffect, useState } from "react";

type AssignFooterProps = {
  mode: "create" | "edit" | "template";
  athleteIds: number[];
  dates: string[];
  description: string;
  saving: boolean;
  error: string | null;
  success: string | null;
  onAthleteIdsChange: (ids: number[]) => void;
  onDatesChange: (dates: string[]) => void;
  onDescriptionChange: (value: string) => void;
  onAssign: () => void;
  onSaveTemplate: () => void;
  onCancel?: () => void;
};

export function AssignFooter({
  mode,
  athleteIds,
  dates,
  description,
  saving,
  error,
  success,
  onAthleteIdsChange,
  onDatesChange,
  onDescriptionChange,
  onAssign,
  onSaveTemplate,
  onCancel,
}: AssignFooterProps) {
  const [roster, setRoster] = useState<CoachAthleteListItem[]>([]);
  const [dateDraft, setDateDraft] = useState(dates[0] ?? todayIso());

  useEffect(() => {
    if (dates[0] && mode === "edit") {
      setDateDraft(dates[0]);
    }
  }, [dates, mode]);

  useEffect(() => {
    if (mode === "template") return;
    listAthletes().then((result) => {
      if (result.success && result.athletes) {
        setRoster(result.athletes);
      }
    });
  }, [mode]);

  function toggleAthlete(id: number) {
    if (athleteIds.includes(id)) {
      onAthleteIdsChange(athleteIds.filter((x) => x !== id));
    } else {
      onAthleteIdsChange([...athleteIds, id]);
    }
  }

  function addDate() {
    if (!dateDraft || dates.includes(dateDraft)) return;
    onDatesChange([...dates, dateDraft].sort());
  }

  function removeDate(iso: string) {
    onDatesChange(dates.filter((d) => d !== iso));
  }

  const primaryAction =
    mode === "template" ? "Save template" : mode === "edit" ? "Save changes" : "Assign";

  return (
    <div className="builder-assign card stack">
      <div className="row-between">
        <h3>{mode === "template" ? "Save" : "Assign"}</h3>
        <span className="muted">
          {mode === "template" ? "persist structure" : "who + when"}
        </span>
      </div>

      {mode !== "template" && (
        <>
          <div className="stack">
            <span className="muted">Athletes</span>
            <div className="builder-athlete-grid">
              {roster.map((item) => (
                <label key={item.athlete.id} className="builder-athlete-option">
                  <input
                    type="checkbox"
                    checked={athleteIds.includes(item.athlete.id)}
                    onChange={() => toggleAthlete(item.athlete.id)}
                    disabled={mode === "edit"}
                  />
                  {item.athlete.name}
                </label>
              ))}
              {roster.length === 0 && <p className="muted">No athletes on your roster yet.</p>}
            </div>
          </div>

          <div className="stack">
            <span className="muted">Dates</span>
            <div className="row-between" style={{ gap: "0.5rem", flexWrap: "wrap" }}>
              <input
                type="date"
                value={mode === "edit" ? (dates[0] ?? dateDraft) : dateDraft}
                onChange={(e) => {
                  const next = e.target.value;
                  setDateDraft(next);
                  if (mode === "edit") {
                    onDatesChange([next]);
                  } else if (dates.length <= 1) {
                    onDatesChange(next ? [next] : []);
                  }
                }}
              />
              {mode === "create" && (
                <button type="button" className="secondary" onClick={addDate}>
                  Add date
                </button>
              )}
            </div>
            {mode === "create" && (
              <div className="builder-date-chips">
                {dates.map((d) => (
                  <span key={d} className="builder-date-chip">
                    {d}
                    <button type="button" className="secondary" onClick={() => removeDate(d)}>
                      ×
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      <label>
        Coach notes
        <textarea
          rows={2}
          value={description}
          onChange={(e) => onDescriptionChange(e.target.value)}
          placeholder="Optional notes for the athlete"
        />
      </label>

      {error && <p className="error">{error}</p>}
      {success && <p className="success">{success}</p>}

      <div className="row-between" style={{ gap: "0.5rem", flexWrap: "wrap" }}>
        {onCancel && (
          <button type="button" className="secondary" onClick={onCancel} disabled={saving}>
            Cancel
          </button>
        )}
        <div className="row-between" style={{ gap: "0.5rem", marginLeft: "auto" }}>
          {mode === "create" && (
            <button type="button" className="secondary" onClick={onSaveTemplate} disabled={saving}>
              Save template
            </button>
          )}
          <button type="button" onClick={onAssign} disabled={saving}>
            {saving ? "Saving…" : primaryAction}
          </button>
        </div>
      </div>
    </div>
  );
}
