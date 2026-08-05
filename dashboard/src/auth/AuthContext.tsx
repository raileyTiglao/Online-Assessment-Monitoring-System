// src/auth/AuthContext.tsx — tracks the signed-in Firebase user AND their
// role, read from the "role" custom claim on their ID token (set by
// connection/bootstrap_admin.py via the Admin SDK — never trust a role
// value that isn't baked into the token itself, since anything else could
// be spoofed by a client-writable field).

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { onAuthStateChanged, type User } from "firebase/auth";
import { auth } from "../firebase";

export type Role = "admin" | "professor" | null;

interface AuthState {
  user: User | null;
  role: Role;
  loading: boolean;
}

const AuthContext = createContext<AuthState>({ user: null, role: null, loading: true });

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ user: null, role: null, loading: true });

  useEffect(() => {
    return onAuthStateChanged(auth, async (user) => {
      if (!user) {
        setState({ user: null, role: null, loading: false });
        return;
      }
      // Force a refresh so a role change from bootstrap_admin.py (e.g. a
      // fresh promotion) is picked up without requiring a manual sign-out —
      // still requires the user to trigger SOME auth state change (e.g.
      // reloading the page), but avoids a stale cached claim within a
      // single already-loaded session being the only option.
      const tokenResult = await user.getIdTokenResult();
      const role = (tokenResult.claims.role as Role) ?? null;
      setState({ user, role, loading: false });
    });
  }, []);

  return <AuthContext.Provider value={state}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
