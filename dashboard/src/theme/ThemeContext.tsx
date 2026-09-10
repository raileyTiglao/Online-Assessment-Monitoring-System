// src/theme/ThemeContext.tsx — explicit dark/light theme state, persisted
// to localStorage and mirrored onto <html data-theme>. Not OS-driven
// (no prefers-color-scheme involvement) — default is dark, matching the
// ported design's own default. index.html has a matching inline pre-paint
// script that reads the same localStorage key before first paint, so this
// provider's lazy initializer always agrees with what's already on <html>.

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

export type Theme = "dark" | "light";

const STORAGE_KEY = "oams-theme";

interface ThemeState {
  theme: Theme;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeState>({ theme: "dark", toggleTheme: () => {} });

function readInitialTheme(): Theme {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved === "light" ? "light" : "dark";
  } catch {
    return "dark";
  }
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(readInitialTheme);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // localStorage unavailable (private browsing, quota) — theme still
      // works for this page load via the data-theme attribute, just won't
      // persist across reloads.
    }
  }, [theme]);

  const toggleTheme = () => setTheme((t) => (t === "dark" ? "light" : "dark"));

  return <ThemeContext.Provider value={{ theme, toggleTheme }}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  return useContext(ThemeContext);
}
