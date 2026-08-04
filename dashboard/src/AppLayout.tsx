// src/AppLayout.tsx — nav shell wrapping every authenticated page: role-
// aware nav links + sign-out. Rendered by a ProtectedRoute-wrapped parent
// route in router.tsx, so `useAuth().user` is guaranteed non-null here.

import { NavLink, Outlet } from "react-router-dom";
import { signOut } from "firebase/auth";
import { auth } from "./firebase";
import { useAuth } from "./auth/AuthContext";

export function AppLayout() {
  const { user, role } = useAuth();

  return (
    <div className="app-shell">
      <nav className="app-nav">
        <span className="app-nav__brand">OAMS Dashboard</span>
        <NavLink to="/" end>Dashboard</NavLink>
        <NavLink to="/sessions">Sessions</NavLink>
        {role === "professor" && <NavLink to="/exams">Exams</NavLink>}
        {role === "admin" && <NavLink to="/admin/users">Users</NavLink>}
        <span className="app-nav__spacer" />
        <span className="app-nav__user">{user?.email} ({role})</span>
        <button type="button" className="button-secondary" onClick={() => signOut(auth)}>
          Sign out
        </button>
      </nav>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
