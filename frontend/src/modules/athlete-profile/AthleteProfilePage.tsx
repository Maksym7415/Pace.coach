import { Link } from "react-router-dom";
import { PersonalInfoSection } from "./PersonalInfoSection";
import { RecoveryBaselinesSection } from "./RecoveryBaselinesSection";
import { SportsSection } from "./SportsSection";

export function AthleteProfilePage() {
  return (
    <div className="stack">
      <p>
        <Link to="/today">← Back to Today</Link>
      </p>

      <div>
        <h1>Performance profile</h1>
        <p className="muted">
          Manage your body metrics, recovery baselines, and sport-specific training configuration.
        </p>
      </div>

      <PersonalInfoSection />
      <RecoveryBaselinesSection />
      <SportsSection />
    </div>
  );
}
