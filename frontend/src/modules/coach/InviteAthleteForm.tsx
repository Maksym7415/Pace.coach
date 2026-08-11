import { FormEvent, useEffect, useState } from "react";
import { inviteAthlete, searchUsers, type SearchUser } from "../coaching/api";
import { SectionBox } from "../shared/PageChrome";

export function InviteAthleteForm() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchUser[]>([]);
  const [searching, setSearching] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (query.trim().length < 2) {
      setResults([]);
      return;
    }

    const timer = window.setTimeout(() => {
      setSearching(true);
      searchUsers(query.trim(), "athlete").then((result) => {
        setSearching(false);
        if (result.success && result.users) {
          setResults(result.users);
        } else {
          setResults([]);
        }
      });
    }, 300);

    return () => window.clearTimeout(timer);
  }, [query]);

  async function onInvite(athleteId: number) {
    setBusyId(athleteId);
    setError(null);
    setMessage(null);
    const result = await inviteAthlete(athleteId);
    setBusyId(null);
    if (!result.success) {
      setError(result.error ?? "Failed to send invitation");
      return;
    }
    setMessage("Invitation sent. The athlete must accept before they appear in your list.");
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
  }

  return (
    <SectionBox label="Invite athlete" note="Search by name or username">
      <p className="mb-2 text-sm text-slate-500">
        Invitations must be accepted by the athlete before they appear on your roster.
      </p>
      <form className="stack" onSubmit={onSubmit}>
        <label>
          Search
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Min 2 characters…"
            autoComplete="off"
          />
        </label>
      </form>
      {searching && <p className="muted">Searching…</p>}
      {results.length > 0 && (
        <ul className="invite-results stack">
          {results.map((user) => (
            <li key={user.id} className="row-between invite-result-row">
              <span>
                <strong>{user.name}</strong> <span className="muted">@{user.username}</span>
              </span>
              <button
                type="button"
                className="secondary"
                disabled={busyId === user.id}
                onClick={() => onInvite(user.id)}
              >
                {busyId === user.id ? "Sending…" : "Invite"}
              </button>
            </li>
          ))}
        </ul>
      )}
      {message && <p className="success">{message}</p>}
      {error && <p className="error">{error}</p>}
    </SectionBox>
  );
}
