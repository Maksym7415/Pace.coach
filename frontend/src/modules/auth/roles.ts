import type { User, UserRole } from "../shared/api";

export function hasRole(user: User | null, role: UserRole): boolean {
  return user?.roles.includes(role) ?? false;
}

export function defaultHomePath(roles: UserRole[]): string {
  if (roles.includes("athlete") || roles.includes("coach")) return "/today";
  return "/today";
}
