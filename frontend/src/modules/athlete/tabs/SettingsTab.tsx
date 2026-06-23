import { StravaConnect } from "../strava/StravaConnect";

export function SettingsTab() {
  return (
    <div className="stack">
      <h2>Settings</h2>
      <div className="card">
        <StravaConnect />
      </div>
      <p className="muted">More profile settings coming soon.</p>
    </div>
  );
}
