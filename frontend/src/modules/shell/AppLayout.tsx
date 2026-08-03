import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { useAuth } from "../auth/AuthContext";
import type { UserRole } from "../shared/api";
import { AppShell } from "./AppShell";

type ViewRoleContextValue = {
  viewRole: UserRole;
  setViewRole: (role: UserRole) => void;
};

const ViewRoleContext = createContext<ViewRoleContextValue | null>(null);

export function useViewRole(): ViewRoleContextValue {
  const ctx = useContext(ViewRoleContext);
  if (!ctx) throw new Error("useViewRole must be used within AppLayout");
  return ctx;
}

export function AppLayout({ children }: { children: ReactNode }) {
  const { hasRole } = useAuth();
  const defaultRole: UserRole = hasRole("athlete") ? "athlete" : "coach";
  const [viewRole, setViewRole] = useState<UserRole>(defaultRole);

  const value = useMemo(() => ({ viewRole, setViewRole }), [viewRole]);

  return (
    <ViewRoleContext.Provider value={value}>
      <AppShell viewRole={viewRole} onViewRoleChange={setViewRole}>
        {children}
      </AppShell>
    </ViewRoleContext.Provider>
  );
}
