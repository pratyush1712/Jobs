/**
 * Theme management — light / dark toggle with localStorage persistence.
 * The active theme is applied as a `dark` class on <html>.
 */

"use client";

import { useCallback, useSyncExternalStore } from "react";

export type Theme = "light" | "dark";

const STORAGE_KEY = "jt-theme";

function resolveTheme(): Theme {
  if (typeof window === "undefined") return "light";
  const stored = localStorage.getItem(STORAGE_KEY) as Theme | null;
  if (stored === "light" || stored === "dark") return stored;
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function applyTheme(theme: Theme) {
  if (typeof document === "undefined") return;
  if (theme === "dark") {
    document.documentElement.classList.add("dark");
  } else {
    document.documentElement.classList.remove("dark");
  }
}

/**
 * Subscribe to theme changes via a custom storage event so any tab / component
 * that calls toggle() stays in sync without a context provider.
 */
const THEME_EVENT = "jt-theme-change";

function subscribe(cb: () => void): () => void {
  window.addEventListener(THEME_EVENT, cb);
  return () => window.removeEventListener(THEME_EVENT, cb);
}

function getSnapshot(): Theme {
  return resolveTheme();
}

function getServerSnapshot(): Theme {
  return "light";
}

/** Hook that provides current theme and a toggle function. */
export function useTheme(): { theme: Theme; toggle: () => void } {
  const theme = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const toggle = useCallback(() => {
    const next: Theme = resolveTheme() === "light" ? "dark" : "light";
    localStorage.setItem(STORAGE_KEY, next);
    applyTheme(next);
    window.dispatchEvent(new Event(THEME_EVENT));
  }, []);

  return { theme, toggle };
}
