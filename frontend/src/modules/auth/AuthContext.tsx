import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { apiGet, getToken, setToken, type User, type UserRole } from "../shared/api";
import { hasRole } from "./roles";

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  setUser: (user: User | null) => void;
  refreshUser: () => Promise<void>;
  logout: () => void;
  hasRole: (role: UserRole) => boolean;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(() => Boolean(getToken()));

  useEffect(() => {
    if (!getToken()) {
      setUser(null);
      setLoading(false);
      return;
    }

    let cancelled = false;
    apiGet<{ user: User }>("/api/auth/me").then((result) => {
      if (cancelled) return;
      if (!result.success || !result.user) {
        setToken(null);
        setUser(null);
      } else {
        setUser(result.user);
      }
      setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    window.location.href = "/login";
  }, []);

  const refreshUser = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      return;
    }
    const result = await apiGet<{ user: User }>("/api/auth/me");
    if (!result.success || !result.user) {
      setToken(null);
      setUser(null);
      return;
    }
    setUser(result.user);
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      setUser,
      refreshUser,
      logout,
      hasRole: (role: UserRole) => hasRole(user, role),
    }),
    [user, loading, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
