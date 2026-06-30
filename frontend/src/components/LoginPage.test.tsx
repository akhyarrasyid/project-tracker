import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { useAuth, useTheme } = vi.hoisted(() => ({
  useAuth: vi.fn(),
  useTheme: vi.fn(),
}));

vi.mock("../contexts/useAuth", () => ({
  useAuth,
}));

vi.mock("../app/theme", async () => {
  const actual = await vi.importActual<typeof import("../app/theme")>("../app/theme");
  return {
    ...actual,
    useTheme,
  };
});

vi.mock("../app/build-info", () => ({
  getBuildLabel: () => "Project Tracker v1.00",
}));

import { LoginPage } from "./LoginPage";

describe("LoginPage", () => {
  const login = vi.fn();
  const toggleTheme = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    useAuth.mockReturnValue({ login });
    useTheme.mockReturnValue({ theme: "dark", toggleTheme });
  });

  it("shows validation feedback for empty credentials", async () => {
    render(<LoginPage />);

    fireEvent.click(screen.getByRole("button", { name: "Masuk ke Workspace" }));

    expect(await screen.findByText("Username/email dan password wajib diisi")).toBeInTheDocument();
  });

  it("submits login credentials", async () => {
    login.mockResolvedValue(undefined);
    render(<LoginPage />);

    fireEvent.change(screen.getByLabelText("Username / Email"), { target: { value: "admin" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secret" } });
    fireEvent.click(screen.getByRole("button", { name: "Masuk ke Workspace" }));

    await waitFor(() => {
      expect(login).toHaveBeenCalledWith("admin", "secret");
    });
    expect(screen.getByTestId("build-identity")).toHaveTextContent("Project Tracker v1.00");
  });

  it("shows the API error detail when login fails", async () => {
    login.mockRejectedValue({
      response: {
        data: {
          detail: "Akun tidak valid",
        },
      },
    });

    render(<LoginPage />);

    fireEvent.change(screen.getByLabelText("Username / Email"), { target: { value: "admin" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secret" } });
    fireEvent.click(screen.getByRole("button", { name: "Masuk ke Workspace" }));

    expect(await screen.findByText("Akun tidak valid")).toBeInTheDocument();
  });

  it("toggles the theme from the header button", () => {
    render(<LoginPage />);

    screen.getByRole("button", { name: "Switch to light mode" }).click();
    expect(toggleTheme).toHaveBeenCalledTimes(1);
    expect(screen.getByPlaceholderText("username atau email Anda")).toBeInTheDocument();
  });
});
