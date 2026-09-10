// src/AppLayout.tsx — shell wrapping every authenticated page: fixed
// sidebar nav + main content area. Rendered by a ProtectedRoute-wrapped
// parent route in router.tsx. Role-aware nav links and sign-out live in
// Sidebar.tsx.

import { Outlet } from "react-router-dom";
import { Sidebar } from "./components/Sidebar";

export function AppLayout() {
  return (
    <div className="app-shell">
      <Sidebar />
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
