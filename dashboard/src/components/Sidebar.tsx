// src/components/Sidebar.tsx — fixed left nav, replaces the old top nav
// bar in AppLayout.tsx. Ported from php_backend's .sidebar design.

import { NavLink } from "react-router-dom";
import { signOut } from "firebase/auth";
import { auth } from "../firebase";
import { useAuth } from "../auth/AuthContext";
import { useTheme } from "../theme/ThemeContext";
import { ThemeToggleStarfield } from "./animations/ThemeToggleStarfield";

function navItemClass({ isActive }: { isActive: boolean }) {
  return isActive ? "nav-item active" : "nav-item";
}

export function Sidebar() {
  const { user, role } = useAuth();
  const { toggleTheme } = useTheme();

  const initial = (user?.email?.[0] ?? "?").toUpperCase();
  const roleLabel = role ? role[0].toUpperCase() + role.slice(1) : "";

  return (
    <aside className="sidebar">
      <div className="sidebar-identity">
        <span className="avatar">{initial}</span>
        <div className="identity-text">
          <span className="identity-name">{user?.email}</span>
          <span className="identity-tag">{roleLabel}</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        <NavLink to="/" end className={navItemClass}>
          <span className="nav-icon">⌂</span>
          Dashboard
        </NavLink>
        <NavLink to="/exams" className={navItemClass}>
          <span className="nav-icon">▤</span>
          Exams &amp; Students
        </NavLink>
        {role === "admin" && (
          <NavLink to="/admin/users" className={navItemClass}>
            <span className="nav-icon">☺</span>
            Users
          </NavLink>
        )}
      </nav>

      <nav className="sidebar-nav sidebar-nav-bottom">
        <button type="button" className="theme-pill" onClick={toggleTheme}>
          <ThemeToggleStarfield />
          <span className="theme-pill__label">
            <span className="theme-toggle-pill__label-dark">Dark mode</span>
            <span className="theme-toggle-pill__label-light">Light mode</span>
          </span>
        </button>
        <button type="button" className="nav-item" onClick={() => signOut(auth)}>
          <span className="nav-icon">⏻</span>
          Sign out
        </button>
      </nav>

      <div className="sidebar-footer">
        <span>HOLY ANGEL UNIVERSITY</span>
        <strong>OAMS Dashboard</strong>
      </div>
    </aside>
  );
}
