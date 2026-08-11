import { useEffect, useState } from "react";
import { listAthletes, type CoachAthleteListItem } from "../coaching/api";
import { PageFrame, SectionBox } from "../shared/PageChrome";
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
    <PageFrame title="Athletes" question="Who am I coaching?">
      <SectionBox label="Roster" note="Pin an athlete to scope every shared workspace">
        {loading && <p className="text-sm text-slate-500">Loading athletes…</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
        {!loading && !error && <AthleteList athletes={athletes} />}
      </SectionBox>

      <InviteAthleteForm />
    </PageFrame>
  );
}
