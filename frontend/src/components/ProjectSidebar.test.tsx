import "@testing-library/jest-dom";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { useAuth, getProjects } = vi.hoisted(() => ({
  useAuth: vi.fn(),
  getProjects: vi.fn(),
}));

vi.mock("../contexts/useAuth", () => ({
  useAuth,
}));

vi.mock("../api/meta", () => ({
  metaApi: {
    getProjects,
  },
}));

import { ProjectSidebar } from "./ProjectSidebar";

describe("ProjectSidebar", () => {
  const onSelectProject = vi.fn();
  const logout = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    useAuth.mockReturnValue({
      user: { username: "admin", full_name: "Demo Admin", role: "admin" },
      logout,
    });
  });

  it("renders the loading state and then project actions", async () => {
    getProjects.mockResolvedValue([
      { id: 1, key: "PAY", name: "Payment Platform" },
    ]);

    render(<ProjectSidebar selectedProjectId={1} onSelectProject={onSelectProject} />);

    expect(screen.getByText("Proyek Workspace")).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: /Payment Platform/i })).toBeInTheDocument();
  });

  it("shows the empty state when there are no projects", async () => {
    getProjects.mockResolvedValue([]);

    render(<ProjectSidebar selectedProjectId={null} onSelectProject={onSelectProject} />);

    expect(await screen.findByText("Belum ada proyek")).toBeInTheDocument();
  });

  it("selects dashboard and project, then logs out", async () => {
    getProjects.mockResolvedValue([{ id: 1, key: "PAY", name: "Payment Platform" }]);

    render(<ProjectSidebar selectedProjectId={null} onSelectProject={onSelectProject} />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Payment Platform/i })).toBeInTheDocument();
    });

    screen.getByRole("button", { name: /Dashboard/i }).click();
    screen.getByRole("button", { name: /Payment Platform/i }).click();
    screen.getByRole("button", { name: /Keluar/i }).click();

    expect(onSelectProject).toHaveBeenCalledWith(null);
    expect(onSelectProject).toHaveBeenCalledWith(1);
    expect(logout).toHaveBeenCalledTimes(1);
  });
});
