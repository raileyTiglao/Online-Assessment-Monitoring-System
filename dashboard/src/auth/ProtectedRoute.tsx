// src/auth/ProtectedRoute.tsx — gates a route by signed-in state and
// (optionally) required role(s). Redirects to /login if not signed in,
// or /unauthorized if signed in but the role doesn't match.

import { Navigate, Outlet } from "react-router-dom";
import { useAuth, type Role } from "./AuthContext";

interface ProtectedRouteProps {
  allowedRoles?: Role[];
}

export function ProtectedRoute({ allowedRoles }: ProtectedRouteProps) {
  const { user, role, loading } = useAuth();

  if (loading) return <div className="page-loading">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (allowedRoles && !allowedRoles.includes(role)) {
    return <Navigate to="/unauthorized" replace />;
  }

  return <Outlet />;
}
