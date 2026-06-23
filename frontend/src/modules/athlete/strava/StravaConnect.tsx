import { useEffect, useState } from "react";
import { useAuth } from "../../auth/AuthContext";
import { disconnect, getConnectUrl, getStatus } from "../../strava/api";

export function StravaConnect() {
  const { user, refreshUser } = useAuth();
  const [athleteId, setAthleteId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user?.strava_connected) {
      setLoading(false);
      return;
    }
    getStatus().then(({ status, error: statusError }) => {
      if (statusError) setError(statusError);
      if (status?.athlete?.id) setAthleteId(status.athlete.id);
      setLoading(false);
    });
  }, [user?.strava_connected]);

  async function onConnect() {
    setBusy(true);
    setError(null);
    const result = await getConnectUrl();
    setBusy(false);
    if (!result.success || !result.authorize_url) {
      setError(result.error ?? "Strava is not available");
      return;
    }
    window.location.href = result.authorize_url;
  }

  async function onDisconnect() {
    setBusy(true);
    setError(null);
    const result = await disconnect();
    setBusy(false);
    if (!result.success) {
      setError(result.error ?? "Failed to disconnect Strava");
      return;
    }
    setAthleteId(null);
    await refreshUser();
  }

  const connected = Boolean(user?.strava_connected);

  return (
    <div className="stack">
      <h3>Strava</h3>
      {loading && connected && <p className="muted">Loading Strava status…</p>}
      {connected ? (
        <>
          <p className="muted">
            Connected{athleteId ? ` (athlete ID ${athleteId})` : ""}. Activities sync via webhook.
          </p>
          <button type="button" className="secondary" onClick={onDisconnect} disabled={busy}>
            {busy ? "Disconnecting…" : "Disconnect Strava"}
          </button>
        </>
      ) : (
        <>
          <p className="muted">Connect Strava to automatically import your runs, rides, and swims.</p>
          <button type="button" onClick={onConnect} disabled={busy}>
            {busy ? "Opening Strava…" : "Connect with Strava"}
          </button>
        </>
      )}
      {error && <p className="error">{error}</p>}
    </div>
  );
}
