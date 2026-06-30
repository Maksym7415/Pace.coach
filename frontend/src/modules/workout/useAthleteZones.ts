import { useEffect, useState } from "react";
import {
  getAthleteSportProfile,
  listAthleteZones,
  type SportProfile,
  type Zone,
} from "../athlete-profile/api";

export function useAthleteZones(athleteId: number, sportId: number | null) {
  const [zones, setZones] = useState<Zone[]>([]);
  const [profile, setProfile] = useState<SportProfile | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!athleteId || !sportId) {
      setZones([]);
      setProfile(null);
      return;
    }

    let cancelled = false;
    setLoading(true);

    Promise.all([
      listAthleteZones(athleteId, sportId),
      getAthleteSportProfile(athleteId, sportId),
    ]).then(([zonesResult, profileResult]) => {
      if (cancelled) return;
      setZones(zonesResult.success ? (zonesResult.zones ?? []) : []);
      setProfile(profileResult.success ? (profileResult.profile ?? null) : null);
      setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, [athleteId, sportId]);

  return { zones, profile, loading };
}
