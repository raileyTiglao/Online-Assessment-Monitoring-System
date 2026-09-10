// src/router.tsx — route table. Every authenticated route sits under the
// AppLayout shell; role gating is ProtectedRoute's job, not individual
// pages'.

import { createBrowserRouter } from "react-router-dom";
import { AppLayout } from "./AppLayout";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { LoginPage } from "./auth/LoginPage";
import { DashboardHome } from "./pages/DashboardHome";
import { ExamsAndSessionsPage } from "./pages/ExamsAndSessionsPage";
import { SessionDetailPage } from "./pages/SessionDetailPage";
import { AdminUsersPage } from "./pages/AdminUsersPage";
import { UnauthorizedPage } from "./pages/UnauthorizedPage";

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/unauthorized", element: <UnauthorizedPage /> },
  {
    element: <ProtectedRoute />, // any signed-in user (admin or professor)
    children: [
      {
        element: <AppLayout />,
        children: [
          { path: "/", element: <DashboardHome /> },
          { path: "/exams", element: <ExamsAndSessionsPage /> },
          { path: "/sessions/:sessionId", element: <SessionDetailPage /> },
          {
            element: <ProtectedRoute allowedRoles={["admin"]} />,
            children: [{ path: "/admin/users", element: <AdminUsersPage /> }],
          },
        ],
      },
    ],
  },
]);
