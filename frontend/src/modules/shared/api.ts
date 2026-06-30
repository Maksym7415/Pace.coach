export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export type ApiEnvelope<T> = {
  success: boolean;
  error?: string;
} & T;

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function apiGet<T>(path: string): Promise<ApiEnvelope<T>> {
  const response = await fetch(`${API_BASE}${path}`, { headers: authHeaders() });
  return response.json();
}

export async function apiPost<T>(path: string, body: unknown): Promise<ApiEnvelope<T>> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  });
  return response.json();
}

export async function apiPut<T>(path: string, body?: unknown): Promise<ApiEnvelope<T>> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  return response.json();
}

export async function apiDelete<T>(path: string): Promise<ApiEnvelope<T>> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  return response.json();
}

export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  return fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { ...authHeaders(), ...init?.headers },
  });
}

export type UserRole = "athlete" | "coach";

export type User = {
  id: number;
  username: string;
  email: string;
  name: string;
  avatar_url: string | null;
  preferred_distance_unit: string;
  roles: UserRole[];
  strava_connected?: boolean;
};

export function setToken(token: string | null) {
  if (token) localStorage.setItem("token", token);
  else localStorage.removeItem("token");
}

export function getToken() {
  return localStorage.getItem("token");
}
