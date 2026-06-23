import { apiFetch, apiGet, apiPost } from "../shared/api";

export type StravaStatus = {
  configured: boolean;
  connected: boolean;
  athlete: { id: number };
};

export function stravaOAuthRedirectUri(): string {
  return `${window.location.origin}/strava/oauth`;
}

export async function getConnectUrl(redirectUri = stravaOAuthRedirectUri()) {
  const params = new URLSearchParams({ redirect_uri: redirectUri });
  return apiGet<{ authorize_url: string }>(`/api/strava/connect?${params}`);
}

export async function getStatus(): Promise<{ status: StravaStatus | null; error?: string }> {
  const response = await apiFetch("/api/strava/status");
  if (response.status === 404) return { status: null };
  const result = await response.json();
  if (!result.success) return { status: null, error: result.error };
  return {
    status: {
      configured: result.configured,
      connected: result.connected,
      athlete: result.athlete,
    },
  };
}

export async function disconnect() {
  return apiPost<Record<string, never>>("/api/strava/disconnect", {});
}
