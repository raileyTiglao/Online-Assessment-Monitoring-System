// src/pages/UnauthorizedPage.tsx — shown when a signed-in user's role
// doesn't match a route's allowedRoles (e.g. a professor hitting /admin/users).

import { Link } from "react-router-dom";

export function UnauthorizedPage() {
  return (
    <div className="page">
      <h1>Not authorized</h1>
      <p>Your account doesn't have access to this page.</p>
      <Link to="/" className="button-secondary">Back to dashboard</Link>
    </div>
  );
}
