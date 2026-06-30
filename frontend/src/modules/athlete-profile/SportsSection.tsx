import { FormEvent, useCallback, useEffect, useState, type ReactNode } from "react";
import {
  addMySport,
  listMySports,
  listSports,
  removeMySport,
  setMyPrimarySport,
  type AthleteSport,
  type Sport,
} from "./api";
import { SportProfileSection } from "./SportProfileSection";

type SportsSectionProps = {
  coachMode?: boolean;
  athleteId?: number;
  fetchAthleteSports?: () => ReturnType<typeof listMySports>;
  fetchAvailableSports?: () => ReturnType<typeof listSports>;
  onAddSport?: (sportId: number, isPrimary: boolean) => ReturnType<typeof addMySport>;
  onRemoveSport?: (sportId: number) => ReturnType<typeof removeMySport>;
  onSetPrimary?: (sportId: number) => ReturnType<typeof setMyPrimarySport>;
  renderSportProfile?: (athleteSport: AthleteSport) => ReactNode;
};

export function SportsSection({
  coachMode = false,
  fetchAthleteSports = listMySports,
  fetchAvailableSports = listSports,
  onAddSport = addMySport,
  onRemoveSport = removeMySport,
  onSetPrimary = setMyPrimarySport,
  renderSportProfile,
}: SportsSectionProps) {
  const [athleteSports, setAthleteSports] = useState<AthleteSport[]>([]);
  const [availableSports, setAvailableSports] = useState<Sport[]>([]);
  const [selectedSportId, setSelectedSportId] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    const [mySportsResult, allSportsResult] = await Promise.all([
      fetchAthleteSports(),
      fetchAvailableSports(),
    ]);

    if (mySportsResult.success && mySportsResult.sports) {
      setAthleteSports(mySportsResult.sports);
    }
    if (allSportsResult.success && allSportsResult.sports) {
      setAvailableSports(allSportsResult.sports);
    }
    setLoading(false);
  }, [fetchAthleteSports, fetchAvailableSports]);

  useEffect(() => {
    load();
  }, [load]);

  const enrolledIds = new Set(athleteSports.map((s) => s.sport.id));
  const addableSports = availableSports.filter((s) => !enrolledIds.has(s.id));

  async function onAdd(event: FormEvent) {
    event.preventDefault();
    if (!selectedSportId) return;
    setBusy(true);
    setError(null);
    const sportId = Number.parseInt(selectedSportId, 10);
    const result = await onAddSport(sportId, athleteSports.length === 0);
    setBusy(false);
    if (!result.success) {
      setError(result.error ?? "Failed to add sport");
      return;
    }
    setSelectedSportId("");
    await load();
  }

  async function onRemove(sportId: number) {
    setBusy(true);
    setError(null);
    const result = await onRemoveSport(sportId);
    setBusy(false);
    if (!result.success) {
      setError(result.error ?? "Failed to remove sport");
      return;
    }
    await load();
  }

  async function onPrimary(sportId: number) {
    setBusy(true);
    setError(null);
    const result = await onSetPrimary(sportId);
    setBusy(false);
    if (!result.success) {
      setError(result.error ?? "Failed to set primary sport");
      return;
    }
    await load();
  }

  return (
    <section className="stack">
      <div className="card stack">
        <h2>Sports</h2>
        <p className="muted">
          {coachMode
            ? "Sports this athlete participates in."
            : "Add sports you train in and select your primary sport."}
        </p>

        {loading ? (
          <p className="muted">Loading sports…</p>
        ) : (
          <>
            {athleteSports.length === 0 ? (
              <p className="muted">No sports added yet.</p>
            ) : (
              <ul className="stack">
                {athleteSports.map((item) => (
                  <li key={item.id} className="row-between athlete-sport-row">
                    <span>
                      <strong>{item.sport.name}</strong>
                      {item.is_primary && <span className="badge badge-ok">Primary</span>}
                    </span>
                    {!coachMode && (
                      <span className="athlete-sport-actions">
                        {!item.is_primary && (
                          <button
                            type="button"
                            className="secondary"
                            disabled={busy}
                            onClick={() => onPrimary(item.sport.id)}
                          >
                            Set primary
                          </button>
                        )}
                        <button
                          type="button"
                          className="secondary"
                          disabled={busy}
                          onClick={() => onRemove(item.sport.id)}
                        >
                          Remove
                        </button>
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            )}

            {!coachMode && addableSports.length > 0 && (
              <form className="row-between athlete-sport-add" onSubmit={onAdd}>
                <label className="flex-grow">
                  Add sport
                  <select
                    value={selectedSportId}
                    onChange={(e) => setSelectedSportId(e.target.value)}
                  >
                    <option value="">Select…</option>
                    {addableSports.map((sport) => (
                      <option key={sport.id} value={sport.id}>
                        {sport.name}
                      </option>
                    ))}
                  </select>
                </label>
                <button type="submit" disabled={busy || !selectedSportId}>
                  Add
                </button>
              </form>
            )}
          </>
        )}
        {error && <p className="error">{error}</p>}
      </div>

      {athleteSports.map((item) =>
        renderSportProfile ? (
          renderSportProfile(item)
        ) : (
          <SportProfileSection key={item.id} athleteSport={item} />
        ),
      )}
    </section>
  );
}
