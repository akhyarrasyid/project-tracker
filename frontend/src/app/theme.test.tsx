import "@testing-library/jest-dom";
import { act, render, renderHook, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it } from "vitest";

import { ThemeProvider } from "./ThemeProvider";
import { resolveInitialTheme, STORAGE_KEY, useTheme } from "./theme";

function Consumer() {
  const { theme, toggleTheme, setTheme } = useTheme();
  return (
    <div>
      <span data-testid="theme">{theme}</span>
      <button type="button" onClick={toggleTheme}>
        toggle
      </button>
      <button type="button" onClick={() => setTheme("light")}>
        light
      </button>
    </div>
  );
}

function wrapper({ children }: { children: ReactNode }) {
  return <ThemeProvider>{children}</ThemeProvider>;
}

describe("theme", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
    document.documentElement.style.colorScheme = "";
  });

  it("resolves the stored theme when available", () => {
    localStorage.setItem(STORAGE_KEY, "light");
    expect(resolveInitialTheme()).toBe("light");
  });

  it("falls back to matchMedia when there is no stored theme", () => {
    window.matchMedia = ((query: string) =>
      ({
        media: query,
        matches: true,
        onchange: null,
        addListener: () => {},
        removeListener: () => {},
        addEventListener: () => {},
        removeEventListener: () => {},
        dispatchEvent: () => false,
      }) as MediaQueryList) as typeof window.matchMedia;

    expect(resolveInitialTheme()).toBe("dark");
  });

  it("throws when useTheme is called outside the provider", () => {
    expect(() => renderHook(() => useTheme())).toThrow("useTheme must be used inside ThemeProvider");
  });

  it("persists and toggles the theme", () => {
    render(
      <ThemeProvider>
        <Consumer />
      </ThemeProvider>,
    );

    expect(screen.getByTestId("theme")).toHaveTextContent("dark");
    act(() => {
      screen.getByRole("button", { name: "toggle" }).click();
    });
    expect(screen.getByTestId("theme")).toHaveTextContent("light");
    expect(localStorage.getItem(STORAGE_KEY)).toBe("light");
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(document.documentElement.style.colorScheme).toBe("light");

    act(() => {
      screen.getByRole("button", { name: "light" }).click();
    });
    expect(screen.getByTestId("theme")).toHaveTextContent("light");
  });

  it("supports hook access through ThemeProvider", () => {
    const { result } = renderHook(() => useTheme(), { wrapper });
    expect(result.current.theme).toBe("dark");
  });
});
