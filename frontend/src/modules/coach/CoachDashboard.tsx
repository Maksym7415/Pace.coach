import { useEffect, useState } from "react";
import { listAthletes, type CoachAthleteListItem } from "../coaching/api";
import { AthleteList } from "./AthleteList";
import { InviteAthleteForm } from "./InviteAthleteForm";

export function CoachDashboard() {
  const [athletes, setAthletes] = useState<CoachAthleteListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listAthletes().then((result) => {
      if (!result.success || !result.athletes) {
        setError(result.error ?? "Failed to load athletes");
      } else {
        setAthletes(result.athletes);
      }
      setLoading(false);
    });
  }, []);

  return (
    <div className="stack">
      <h1>Coach dashboard</h1>
      <p className="muted">Manage your athletes and schedule their training.</p>

      <section className="stack">
        <h2>Your athletes</h2>
        {loading && <p className="muted">Loading athletes…</p>}
        {error && <p className="error">{error}</p>}
        {!loading && !error && <AthleteList athletes={athletes} />}
      </section>

      <InviteAthleteForm />
    </div>
  );
}
