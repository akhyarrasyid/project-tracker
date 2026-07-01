import { useEffect, useMemo, useState, type PropsWithChildren } from "react";

import { STORAGE_KEY, ThemeContext, type ThemeContextValue, resolveInitialTheme, type AppTheme } from "./theme";

export function ThemeProvider({ children }: PropsWithChildren) {
  const [theme, setThemeState] = useState<AppTheme>(resolveInitialTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    globalThis.localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  const value = useMemo<ThemeContextValue>(
    () => ({
      theme,
      setTheme: setThemeState,
      toggleTheme: () => setThemeState((current) => (current === "dark" ? "light" : "dark")),
    }),
    [theme],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}
