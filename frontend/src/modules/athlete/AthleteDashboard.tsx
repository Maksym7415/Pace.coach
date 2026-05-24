import { useEffect, useState } from "react";
import { apiGet, User } from "../shared/api";

export function AthleteDashboard() {
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<{ user: User }>("/api/auth/me").then((result) => {
      if (!result.success || !result.user) {
        setError(result.error ?? "Failed to load profile");
        return;
      }
      setUser(result.user);
    });
  }, []);

  return (
    <div className="stack">
      <h1>Athlete dashboard</h1>
      <div className="card stack">
        <p className="muted">MVP placeholder — today workout, readiness, calendar, recovery, AI chat.</p>
        {error && <p className="error">{error}</p>}
        {user && (
          <p>
            Signed in as <strong>{user.name}</strong> ({user.email})
          </p>
        )}
      </div>
    </div>
  );
}
