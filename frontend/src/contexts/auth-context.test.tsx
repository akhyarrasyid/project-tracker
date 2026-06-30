import "@testing-library/jest-dom";
import { act, render, renderHook, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { authApi } = vi.hoisted(() => ({
  authApi: {
    login: vi.fn(),
    getMe: vi.fn(),
  },
}));

vi.mock("../api/auth", () => ({
  authApi,
}));

import { AuthProvider } from "./AuthContext";
import { useAuth } from "./useAuth";

function Consumer() {
  const { user, loading, login, logout } = useAuth();
  return (
    <div>
      <span data-testid="loading">{String(loading)}</span>
      <span data-testid="user">{user?.full_name ?? "none"}</span>
      <button type="button" onClick={() => void login("admin", "secret")}>
        login
      </button>
      <button type="button" onClick={logout}>
        logout
      </button>
    </div>
  );
}

function wrapper({ children }: { children: ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}

describe("Auth context", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it("throws when useAuth is used outside the provider", () => {
    expect(() => renderHook(() => useAuth())).toThrow("useAuth must be used within an AuthProvider");
  });

  it("stops loading immediately when there is no access token", async () => {
    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("loading")).toHaveTextContent("false");
    });
    expect(authApi.getMe).not.toHaveBeenCalled();
  });

  it("loads the current user when a token exists", async () => {
    localStorage.setItem("access_token", "token");
    authApi.getMe.mockResolvedValue({ id: 1, full_name: "Demo Admin" });

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>,
    );

    expect(await screen.findByTestId("user")).toHaveTextContent("Demo Admin");
    expect(authApi.getMe).toHaveBeenCalledTimes(1);
  });

  it("clears invalid tokens when loading the profile fails", async () => {
    localStorage.setItem("access_token", "token");
    localStorage.setItem("refresh_token", "refresh");
    authApi.getMe.mockRejectedValue(new Error("expired"));

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("loading")).toHaveTextContent("false");
    });
    expect(localStorage.getItem("access_token")).toBeNull();
    expect(localStorage.getItem("refresh_token")).toBeNull();
  });

  it("logs in and stores tokens before loading the profile", async () => {
    authApi.login.mockResolvedValue({
      access_token: "access",
      refresh_token: "refresh",
    });
    authApi.getMe.mockResolvedValue({ id: 7, full_name: "Administrator" });

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>,
    );

    await act(async () => {
      screen.getByRole("button", { name: "login" }).click();
    });

    expect(authApi.login).toHaveBeenCalledWith("admin", "secret");
    expect(localStorage.getItem("access_token")).toBe("access");
    expect(localStorage.getItem("refresh_token")).toBe("refresh");
    expect(screen.getByTestId("user")).toHaveTextContent("Administrator");
  });

  it("clears the user when login fails", async () => {
    authApi.login.mockRejectedValue(new Error("boom"));

    const { result } = renderHook(() => useAuth(), { wrapper });

    await expect(result.current.login("admin", "secret")).rejects.toThrow("boom");
    expect(result.current.user).toBeNull();
  });

  it("logs out and clears tokens", async () => {
    authApi.login.mockResolvedValue({
      access_token: "access",
      refresh_token: "refresh",
    });
    authApi.getMe.mockResolvedValue({ id: 7, full_name: "Administrator" });

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>,
    );

    await act(async () => {
      screen.getByRole("button", { name: "login" }).click();
    });
    act(() => {
      screen.getByRole("button", { name: "logout" }).click();
    });

    await waitFor(() => {
      expect(screen.getByTestId("user")).toHaveTextContent("none");
    });
    expect(localStorage.getItem("access_token")).toBeNull();
    expect(localStorage.getItem("refresh_token")).toBeNull();
  });
});
