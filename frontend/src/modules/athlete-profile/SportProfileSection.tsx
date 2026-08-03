import { FormEvent, useEffect, useState } from "react";
import {
  ZONE_CATEGORIES,
  ZONE_SOURCES,
  createMyZone,
  deleteMyZone,
  getMySportProfile,
  listMyZones,
  mmssToSecs,
  secsToMMSS,
  upsertMySportProfile,
  type AthleteSport,
  type Zone,
  type ZoneCategory,
  type ZoneSource,
} from "./api";

type SportProfileSectionProps = {
  athleteSport: AthleteSport;
  coachMode?: boolean;
  athleteId?: number;
  getSportProfile?: (sportId: number) => ReturnType<typeof getMySportProfile>;
  saveSportProfile?: (
    sportId: number,
    data: Parameters<typeof upsertMySportProfile>[1],
  ) => ReturnType<typeof upsertMySportProfile>;
  fetchZones?: (sportId: number) => ReturnType<typeof listMyZones>;
  addZone?: (
    sportId: number,
    data: Parameters<typeof createMyZone>[1],
  ) => ReturnType<typeof createMyZone>;
  removeZone?: (zoneId: number) => ReturnType<typeof deleteMyZone>;
};

export function SportProfileSection({
  athleteSport,
  coachMode = false,
  getSportProfile = getMySportProfile,
  saveSportProfile = upsertMySportProfile,
  fetchZones = listMyZones,
  addZone = createMyZone,
  removeZone = deleteMyZone,
}: SportProfileSectionProps) {
  const sport = athleteSport.sport;
  const [expanded, setExpanded] = useState(athleteSport.is_primary);
  const [thresholdPace, setThresholdPace] = useState("");
  const [thresholdHr, setThresholdHr] = useState("");
  const [ftpWatts, setFtpWatts] = useState("");
  const [cssPace, setCssPace] = useState("");
  const [zoneSource, setZoneSource] = useState<ZoneSource>("manual");
  const [zones, setZones] = useState<Zone[]>([]);
  const [zoneCategory, setZoneCategory] = useState<ZoneCategory>("hr");
  const [zoneName, setZoneName] = useState("");
  const [zoneMin, setZoneMin] = useState("");
  const [zoneMax, setZoneMax] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [zoneSaving, setZoneSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function loadProfile() {
    setLoading(true);
    setError(null);
    try {
      const [profileResult, zonesResult] = await Promise.all([
        getSportProfile(sport.id),
        fetchZones(sport.id),
      ]);

      if (profileResult.success && profileResult.profile) {
        const p = profileResult.profile;
        setThresholdPace(
          p.threshold_pace_sec_per_km != null ? secsToMMSS(p.threshold_pace_sec_per_km) : "",
        );
        setThresholdHr(p.threshold_hr != null ? String(p.threshold_hr) : "");
        setFtpWatts(p.ftp_watts != null ? String(p.ftp_watts) : "");
        setCssPace(
          p.css_pace_sec_per_100m != null ? secsToMMSS(p.css_pace_sec_per_100m) : "",
        );
        setZoneSource(p.zone_source ?? "manual");
      }

      if (zonesResult.success && zonesResult.zones) {
        setZones(zonesResult.zones);
      }
    } catch {
      setError("Failed to load sport profile");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (expanded) {
      loadProfile();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expanded, sport.id]);

  async function onSaveProfile(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);

    const data: Parameters<typeof upsertMySportProfile>[1] = {
      zone_source: zoneSource,
    };

    if (sport.code === "running") {
      const paceSecs = thresholdPace.trim() ? mmssToSecs(thresholdPace) : null;
      if (thresholdPace.trim() && paceSecs == null) {
        setSaving(false);
        setError("Invalid threshold pace format (use mm:ss)");
        return;
      }
      data.threshold_pace_sec_per_km = paceSecs;
      data.threshold_hr = thresholdHr.trim() ? Number.parseInt(thresholdHr, 10) : null;
    } else if (sport.code === "cycling") {
      data.ftp_watts = ftpWatts.trim() ? Number.parseInt(ftpWatts, 10) : null;
      data.threshold_hr = thresholdHr.trim() ? Number.parseInt(thresholdHr, 10) : null;
    } else if (sport.code === "swimming") {
      const paceSecs = cssPace.trim() ? mmssToSecs(cssPace) : null;
      if (cssPace.trim() && paceSecs == null) {
        setSaving(false);
        setError("Invalid CSS pace format (use mm:ss)");
        return;
      }
      data.css_pace_sec_per_100m = paceSecs;
    }

    const result = await saveSportProfile(sport.id, data);
    setSaving(false);
    if (!result.success) {
      setError(result.error ?? "Failed to save sport profile");
      return;
    }
    setSuccess("Sport profile saved");
  }

  async function onAddZone(event: FormEvent) {
    event.preventDefault();
    setZoneSaving(true);
    setError(null);

    const min = Number.parseFloat(zoneMin);
    const max = Number.parseFloat(zoneMax);
    if (Number.isNaN(min) || Number.isNaN(max)) {
      setZoneSaving(false);
      setError("Zone min and max must be numbers");
      return;
    }

    const result = await addZone(sport.id, {
      zone_category: zoneCategory,
      zone_name: zoneName.trim(),
      min_value: min,
      max_value: max,
    });

    setZoneSaving(false);
    if (!result.success) {
      setError(result.error ?? "Failed to add zone");
      return;
    }

    setZoneName("");
    setZoneMin("");
    setZoneMax("");
    const zonesResult = await fetchZones(sport.id);
    if (zonesResult.success && zonesResult.zones) {
      setZones(zonesResult.zones);
    }
  }

  async function onDeleteZone(zoneId: number) {
    const result = await removeZone(zoneId);
    if (!result.success) {
      setError(result.error ?? "Failed to delete zone");
      return;
    }
    setZones((current) => current.filter((z) => z.id !== zoneId));
  }

  return (
    <div className="card stack sport-profile-card">
      <button
        type="button"
        className="sport-profile-toggle row-between"
        onClick={() => setExpanded((v) => !v)}
      >
        <span>
          <strong>{sport.name}</strong>
          {athleteSport.is_primary && <span className="badge badge-ok">Primary</span>}
        </span>
        <span className="muted">{expanded ? "▲" : "▼"}</span>
      </button>

      {expanded && (
        <div className="stack">
          {loading ? (
            <p className="muted">Loading profile…</p>
          ) : (
            <form className="stack" onSubmit={onSaveProfile}>
              {sport.code === "running" && (
                <div className="form-grid">
                  <label>
                    Threshold pace (mm:ss / km)
                    <input
                      placeholder="4:15"
                      value={thresholdPace}
                      onChange={(e) => setThresholdPace(e.target.value)}
                    />
                  </label>
                  <label>
                    Threshold HR (bpm)
                    <input
                      type="number"
                      min={40}
                      max={220}
                      value={thresholdHr}
                      onChange={(e) => setThresholdHr(e.target.value)}
                    />
                  </label>
                </div>
              )}

              {sport.code === "cycling" && (
                <div className="form-grid">
                  <label>
                    FTP (watts)
                    <input
                      type="number"
                      min={1}
                      value={ftpWatts}
                      onChange={(e) => setFtpWatts(e.target.value)}
                    />
                  </label>
                  <label>
                    Threshold HR (bpm)
                    <input
                      type="number"
                      min={40}
                      max={220}
                      value={thresholdHr}
                      onChange={(e) => setThresholdHr(e.target.value)}
                    />
                  </label>
                </div>
              )}

              {sport.code === "swimming" && (
                <label>
                  CSS pace (mm:ss / 100m)
                  <input
                    placeholder="1:45"
                    value={cssPace}
                    onChange={(e) => setCssPace(e.target.value)}
                  />
                </label>
              )}

              <label>
                Zone source
                <select
                  value={zoneSource}
                  onChange={(e) => setZoneSource(e.target.value as ZoneSource)}
                >
                  {ZONE_SOURCES.map((source) => (
                    <option key={source.value} value={source.value}>
                      {source.label}
                    </option>
                  ))}
                </select>
              </label>

              {error && <p className="error">{error}</p>}
              {success && <p className="success">{success}</p>}
              <button type="submit" disabled={saving}>
                {saving ? "Saving…" : coachMode ? "Save athlete profile" : "Save profile"}
              </button>
            </form>
          )}

          <div className="stack">
            <h4>Training zones</h4>
            {zones.length === 0 ? (
              <p className="muted">No zones configured yet.</p>
            ) : (
              <table className="zones-table">
                <thead>
                  <tr>
                    <th>Category</th>
                    <th>Zone</th>
                    <th>Min</th>
                    <th>Max</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {zones.map((zone) => (
                    <tr key={zone.id}>
                      <td>{zone.zone_category}</td>
                      <td>{zone.zone_name}</td>
                      <td>{zone.min_value}</td>
                      <td>{zone.max_value}</td>
                      <td>
                        {!coachMode && (
                          <button
                            type="button"
                            className="secondary"
                            onClick={() => onDeleteZone(zone.id)}
                          >
                            Remove
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            <form className="stack zone-add-form" onSubmit={onAddZone}>
              <div className="form-grid">
                <label>
                  Category
                  <select
                    value={zoneCategory}
                    onChange={(e) => setZoneCategory(e.target.value as ZoneCategory)}
                  >
                    {ZONE_CATEGORIES.map((cat) => (
                      <option key={cat.value} value={cat.value}>
                        {cat.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Zone name
                  <input value={zoneName} onChange={(e) => setZoneName(e.target.value)} required />
                </label>
                <label>
                  Min
                  <input
                    type="number"
                    step="any"
                    value={zoneMin}
                    onChange={(e) => setZoneMin(e.target.value)}
                    required
                  />
                </label>
                <label>
                  Max
                  <input
                    type="number"
                    step="any"
                    value={zoneMax}
                    onChange={(e) => setZoneMax(e.target.value)}
                    required
                  />
                </label>
              </div>
              <button type="submit" className="secondary" disabled={zoneSaving}>
                {zoneSaving ? "Adding…" : "Add zone"}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
