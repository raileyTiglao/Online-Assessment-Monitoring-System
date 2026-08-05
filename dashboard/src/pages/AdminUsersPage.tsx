// src/pages/AdminUsersPage.tsx — admin-only. Lists provisioned accounts
// (the users/{uid} collection, mirrored from Auth custom claims by
// connection/bootstrap_admin.py) and lets an admin soft-disable one via
// the `active` flag. There's no create-account UI here by design — see
// the plan's "script-only provisioning" decision; creating/promoting
// accounts is bootstrap_admin.py's job, this page is read/toggle only.

import { useEffect, useState } from "react";
import { collection, doc, onSnapshot, orderBy, query, updateDoc } from "firebase/firestore";
import { db } from "../firebase";

interface UserDoc {
  uid: string;
  email: string;
  displayName: string;
  role: "admin" | "professor";
  active: boolean;
}

export function AdminUsersPage() {
  const [users, setUsers] = useState<UserDoc[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const q = query(collection(db, "users"), orderBy("email"));
    return onSnapshot(
      q,
      (snapshot) => {
        setUsers(snapshot.docs.map((d) => ({ uid: d.id, ...d.data() }) as UserDoc));
        setLoading(false);
      },
      (err) => {
        setError(err.message);
        setLoading(false);
      },
    );
  }, []);

  async function toggleActive(uid: string, active: boolean) {
    await updateDoc(doc(db, "users", uid), { active });
  }

  return (
    <div className="page">
      <h1>Users</h1>

      {loading && <p className="page-loading">Loading users…</p>}
      {error && <p className="page-error">Couldn't load users: {error}</p>}
      {!loading && !error && users.length === 0 && (
        <p className="empty-state">
          No provisioned accounts yet — use{" "}
          <code>python -m connection.bootstrap_admin create-professor …</code> to create one.
        </p>
      )}

      <table className="exam-table">
        <thead>
          <tr>
            <th>Email</th>
            <th>Name</th>
            <th>Role</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.uid}>
              <td>{u.email}</td>
              <td>{u.displayName || "—"}</td>
              <td>{u.role}</td>
              <td>{u.active ? "Active" : "Disabled"}</td>
              <td>
                <button
                  type="button"
                  className="button-secondary"
                  onClick={() => toggleActive(u.uid, !u.active)}
                >
                  {u.active ? "Disable" : "Enable"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
