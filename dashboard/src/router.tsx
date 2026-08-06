// src/router.tsx — route table. Every authenticated route sits under the
// AppLayout shell; role gating is ProtectedRoute's job, not individual
// pages'.

import { createBrowserRouter } from "react-router-dom";
import { AppLayout } from "./AppLayout";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { LoginPage } from "./auth/LoginPage";
import { DashboardHome } from "./pages/DashboardHome";
import { SessionsListPage } from "./pages/SessionsListPage";
import { SessionDetailPage } from "./pages/SessionDetailPage";
import { ExamsPage } from "./pages/ExamsPage";
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
          { path: "/sessions", element: <SessionsListPage /> },
          { path: "/sessions/:sessionId", element: <SessionDetailPage /> },
          {
            element: <ProtectedRoute allowedRoles={["professor"]} />,
            children: [{ path: "/exams", element: <ExamsPage /> }],
          },
          {
            element: <ProtectedRoute allowedRoles={["admin"]} />,
            children: [{ path: "/admin/users", element: <AdminUsersPage /> }],
          },
        ],
      },
    ],
  },
]);
