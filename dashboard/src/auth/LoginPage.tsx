// src/auth/LoginPage.tsx — sign-in only, no sign-up. Accounts are
// provisioned exclusively via connection/bootstrap_admin.py (see plan:
// script-only provisioning, no Cloud Functions / Blaze plan needed).

import { useState, type FormEvent } from "react";
import { useNavigate, useLocation, Navigate } from "react-router-dom";
import { signInWithEmailAndPassword } from "firebase/auth";
import { auth } from "../firebase";
import { useAuth } from "./AuthContext";

export function LoginPage() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!loading && user) {
    const from = (location.state as { from?: string })?.from ?? "/";
    return <Navigate to={from} replace />;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await signInWithEmailAndPassword(auth, email, password);
      navigate("/", { replace: true });
    } catch {
      // Deliberately vague — don't reveal whether the email exists.
      setError("Invalid email or password.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-page">
      <form className="login-form" onSubmit={handleSubmit}>
        <h1>Online Assessment Monitoring System</h1>
        <p className="login-subtitle">Professor / Admin Dashboard</p>

        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoComplete="email"
        />

        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoComplete="current-password"
        />

        {error && <p className="login-error">{error}</p>}

        <button type="submit" disabled={submitting}>
          {submitting ? "Signing in…" : "Sign in"}
        </button>

        <p className="login-note">
          Don't have an account? Ask your administrator to create one for you.
        </p>
      </form>
    </div>
  );
}
