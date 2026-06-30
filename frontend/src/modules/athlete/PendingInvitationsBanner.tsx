import { useEffect, useState } from "react";
import {
  acceptInvitation,
  listPendingInvitations,
  rejectInvitation,
  type PendingInvitation,
} from "../coaching/api";

export function PendingInvitationsBanner() {
  const [invitations, setInvitations] = useState<PendingInvitation[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listPendingInvitations().then((result) => {
      if (result.success && result.invitations) {
        setInvitations(result.invitations);
      }
      setLoading(false);
    });
  }, []);

  async function onAccept(relationId: number) {
    setBusyId(relationId);
    setError(null);
    const result = await acceptInvitation(relationId);
    setBusyId(null);
    if (!result.success) {
      setError(result.error ?? "Failed to accept invitation");
      return;
    }
    setInvitations((prev) => prev.filter((inv) => inv.relation_id !== relationId));
  }

  async function onReject(relationId: number) {
    setBusyId(relationId);
    setError(null);
    const result = await rejectInvitation(relationId);
    setBusyId(null);
    if (!result.success) {
      setError(result.error ?? "Failed to decline invitation");
      return;
    }
    setInvitations((prev) => prev.filter((inv) => inv.relation_id !== relationId));
  }

  if (loading || invitations.length === 0) {
    return error && !loading ? <p className="error">{error}</p> : null;
  }

  return (
    <div className="stack invitation-banners">
      {invitations.map((invitation) => (
        <div key={invitation.relation_id} className="invitation-banner card row-between">
          <div>
            <strong>Coach invitation</strong>
            <p className="muted">
              <strong>{invitation.coach.name}</strong> (@{invitation.coach.username}) wants to
              coach you.
            </p>
          </div>
          <div className="invitation-actions">
            <button
              type="button"
              disabled={busyId === invitation.relation_id}
              onClick={() => onAccept(invitation.relation_id)}
            >
              {busyId === invitation.relation_id ? "…" : "Accept"}
            </button>
            <button
              type="button"
              className="secondary"
              disabled={busyId === invitation.relation_id}
              onClick={() => onReject(invitation.relation_id)}
            >
              Decline
            </button>
          </div>
        </div>
      ))}
      {error && <p className="error">{error}</p>}
    </div>
  );
}
