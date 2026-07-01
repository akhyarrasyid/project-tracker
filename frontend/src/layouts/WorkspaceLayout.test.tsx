import "@testing-library/jest-dom";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const {
  authState,
  themeState,
  projectsQuery,
  unreadCountQuery,
  loginPage,
} = vi.hoisted(() => ({
  authState: {
    user: { full_name: "Demo Admin", role: "ADMIN" } as
      | { full_name: string; role: string }
      | null,
    loading: false,
    logout: vi.fn(),
  },
  themeState: {
    theme: "dark" as "dark" | "light",
    toggleTheme: vi.fn(),
  },
  projectsQuery: vi.fn(),
  unreadCountQuery: vi.fn(),
  loginPage: vi.fn(() => <div>Mocked login page</div>),
}));

vi.mock("../contexts/useAuth", () => ({
  useAuth: () => authState,
}));

vi.mock("../app/theme", () => ({
  useTheme: () => themeState,
}));

vi.mock("../features/projects/hooks/useProjectsQuery", () => ({
  useProjectsQuery: projectsQuery,
}));

vi.mock("../features/notifications/hooks/useUnreadNotificationCountQuery", () => ({
  useUnreadNotificationCountQuery: unreadCountQuery,
}));

vi.mock("../components/LoginPage", () => ({
  LoginPage: loginPage,
}));

import { WorkspaceLayout } from "./WorkspaceLayout";

describe("WorkspaceLayout", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authState.loading = false;
    authState.user = { full_name: "Demo Admin", role: "ADMIN" };
    themeState.theme = "dark";
    projectsQuery.mockReturnValue({
      data: [
        { id: 1, key: "PAY", name: "Payment Platform" },
        { id: 2, key: "IAM", name: "Identity & Access" },
      ],
      isLoading: false,
    });
    unreadCountQuery.mockReturnValue({
      data: { unread_count: 124 },
    });
  });

  function renderLayout() {
    return render(
      <MemoryRouter>
        <WorkspaceLayout />
      </MemoryRouter>,
    );
  }

  it("renders loading state while auth is resolving", () => {
    authState.loading = true;

    renderLayout();

    expect(screen.getByText("Memuat workspace...")).toBeInTheDocument();
  });

  it("renders the login page when no authenticated user exists", () => {
    authState.user = null;

    renderLayout();

    expect(screen.getByText("Mocked login page")).toBeInTheDocument();
  });

  it("renders navigation, caps unread badge, toggles theme, and logs out", () => {
    renderLayout();

    expect(screen.getByText("Project Tracker")).toBeInTheDocument();
    expect(screen.getByText("Operational workspace")).toBeInTheDocument();
    expect(screen.getAllByText("99+")).toHaveLength(1);
    expect(screen.getByText("Payment Platform")).toBeInTheDocument();
    expect(screen.getByText("Identity & Access")).toBeInTheDocument();
    expect(screen.getByTestId("build-identity")).toHaveTextContent("Project Tracker v1.00");

    fireEvent.click(screen.getByRole("button", { name: /switch to light mode/i }));
    expect(themeState.toggleTheme).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: "Keluar" }));
    expect(authState.logout).toHaveBeenCalledTimes(1);
  });

  it("shows project loading state when projects are still fetching", () => {
    projectsQuery.mockReturnValueOnce({
      data: [],
      isLoading: true,
    });

    renderLayout();

    expect(screen.getByText("Memuat proyek...")).toBeInTheDocument();
  });
});
