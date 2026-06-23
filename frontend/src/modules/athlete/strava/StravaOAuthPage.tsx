import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { getStatus } from "../../strava/api";

type PagePhase = "loading" | "success" | "error" | "still_connected";

const REASON_MESSAGES: Record<string, string> = {
  denied: "You cancelled Strava authorization.",
  exchange_failed: "Strava authorization failed. Please try again.",
  invalid_state: "Invalid or expired authorization session. Please try again.",
};

function messageForReason(reason: string | null, fallback: string): string {
  if (reason && REASON_MESSAGES[reason]) return REASON_MESSAGES[reason];
  return fallback;
}

export function StravaOAuthPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { refreshUser } = useAuth();
  const [phase, setPhase] = useState<PagePhase>("loading");
  const [message, setMessage] = useState("");

  const callbackOutcome = searchParams.get("strava");
  const callbackReason = searchParams.get("reason");

  useEffect(() => {
    let timer: number | undefined;
    let cancelled = false;

    async function verify() {
      await refreshUser();
      const { status } = await getStatus();
      if (cancelled) return;

      const connected = Boolean(status?.connected);

      if (callbackOutcome === "connected" && connected) {
        setPhase("success");
        timer = window.setTimeout(() => navigate("/athlete", { replace: true }), 2000);
        return;
      }

      if (callbackOutcome === "error" && connected) {
        setPhase("still_connected");
        setMessage(
          messageForReason(
            callbackReason,
            "Strava re-authorization failed, but your account is still linked.",
          ),
        );
        return;
      }

      if (callbackOutcome === "error") {
        setPhase("error");
        setMessage(
          messageForReason(callbackReason, "Strava authorization failed. Please try again."),
        );
        return;
      }

      if (callbackOutcome === "connected" && !connected) {
        setPhase("error");
        setMessage("Connection could not be verified. Please try again in Settings.");
        return;
      }

      if (connected) {
        setPhase("success");
        timer = window.setTimeout(() => navigate("/athlete", { replace: true }), 2000);
        return;
      }

      setPhase("error");
      setMessage("Strava is not connected. Connect from Settings.");
    }

    verify().catch(() => {
      if (!cancelled) {
        setPhase("error");
        setMessage("Could not verify Strava connection. Please try again.");
      }
    });

    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [refreshUser, navigate, callbackOutcome, callbackReason]);

  if (phase === "loading") {
    return (
      <div className="card stack">
        <h1>Connecting Strava</h1>
        <p className="muted">Verifying your Strava connection…</p>
      </div>
    );
  }

  if (phase === "success") {
    return (
      <div className="card stack">
        <h1>Strava connected</h1>
        <p className="muted">Your Strava account is linked. Redirecting to your dashboard…</p>
        <button type="button" onClick={() => navigate("/athlete", { replace: true })}>
          Go to dashboard
        </button>
      </div>
    );
  }

  if (phase === "still_connected") {
    return (
      <div className="card stack">
        <h1>Strava still connected</h1>
        <p className="muted">{message}</p>
        <button type="button" onClick={() => navigate("/athlete", { replace: true })}>
          Go to dashboard
        </button>
      </div>
    );
  }

  return (
    <div className="card stack">
      <h1>Strava connection failed</h1>
      <p className="error">{message}</p>
      <button type="button" onClick={() => navigate("/athlete", { replace: true })}>
        Back to dashboard
      </button>
    </div>
  );
}
