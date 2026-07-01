import { createContext, useContext } from "react";

export type AppTheme = "dark" | "light";

export interface ThemeContextValue {
  readonly theme: AppTheme;
  readonly setTheme: (theme: AppTheme) => void;
  readonly toggleTheme: () => void;
}

export const STORAGE_KEY = "project-tracker-theme";

export const ThemeContext = createContext<ThemeContextValue | null>(null);

const getWindow = () => (typeof globalThis.window === "undefined" ? null : globalThis.window);

export function resolveInitialTheme(): AppTheme {
  const browserWindow = getWindow();
  if (!browserWindow) {
    return "dark";
  }

  const storedTheme = browserWindow.localStorage.getItem(STORAGE_KEY);
  if (storedTheme === "dark" || storedTheme === "light") {
    return storedTheme;
  }

  if (typeof browserWindow.matchMedia === "function") {
    return browserWindow.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  return "dark";
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used inside ThemeProvider");
  }
  return context;
}
