import { Link } from "react-router-dom";
import { StravaConnect } from "../strava/StravaConnect";

export function SettingsTab() {
  return (
    <div className="stack">
      <h2>Settings</h2>
      <div className="card">
        <StravaConnect />
      </div>
      <div className="card stack">
        <h3>Performance profile</h3>
        <p className="muted">
          Manage body metrics, recovery baselines, sports, and training zones.
        </p>
        <Link to="/athlete/profile" className="button-link">
          Open performance profile
        </Link>
        <Link to="/today" className="button-link">
          Back to Today
        </Link>
      </div>
    </div>
  );
}
