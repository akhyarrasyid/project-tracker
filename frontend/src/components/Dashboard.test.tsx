import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { useAuth, useProjectsQuery, useMyIssuesQuery } = vi.hoisted(() => ({
  useAuth: vi.fn(),
  useProjectsQuery: vi.fn(),
  useMyIssuesQuery: vi.fn(),
}));

vi.mock("../contexts/useAuth", () => ({
  useAuth,
}));

vi.mock("../features/projects/hooks/useProjectsQuery", () => ({
  useProjectsQuery,
}));

vi.mock("../features/issues/hooks/useMyIssuesQuery", () => ({
  useMyIssuesQuery,
}));

import { Dashboard } from "./Dashboard";

describe("Dashboard", () => {
  const onSelectProject = vi.fn();
  const onTaskClick = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    useAuth.mockReturnValue({
      user: { id: 7, full_name: "Demo Admin" },
    });
  });

  it("renders loading states", () => {
    useProjectsQuery.mockReturnValue({ data: undefined, isLoading: true });
    useMyIssuesQuery.mockReturnValue({ data: undefined, isLoading: true });

    render(<Dashboard onSelectProject={onSelectProject} onTaskClick={onTaskClick} />);

    expect(screen.getByText("Tugas Saya")).toBeInTheDocument();
    expect(screen.getByText("Proyek Saya")).toBeInTheDocument();
  });

  it("renders empty states", () => {
    useProjectsQuery.mockReturnValue({ data: [], isLoading: false });
    useMyIssuesQuery.mockReturnValue({ data: { items: [] }, isLoading: false });

    render(<Dashboard onSelectProject={onSelectProject} onTaskClick={onTaskClick} />);

    expect(screen.getByText("Semua Tugas Selesai!")).toBeInTheDocument();
    expect(screen.getByText("Anda belum tergabung dalam proyek apa pun.")).toBeInTheDocument();
  });

  it("opens tasks and projects from buttons", () => {
    const task = {
      id: 12,
      key: "PAY-12",
      title: "Handle duplicate callback",
      priority: "High",
      status: "In Progress",
      due_date: "2026-07-05",
    };
    const project = {
      id: 1,
      key: "PAY",
      name: "Payment Platform",
      status: "ACTIVE",
    };

    useProjectsQuery.mockReturnValue({ data: [project], isLoading: false });
    useMyIssuesQuery.mockReturnValue({ data: { items: [task] }, isLoading: false });

    render(<Dashboard onSelectProject={onSelectProject} onTaskClick={onTaskClick} />);

    screen.getByRole("button", { name: /Handle duplicate callback/i }).click();
    expect(onTaskClick).toHaveBeenCalledWith(task);

    screen.getByRole("button", { name: /Payment Platform/i }).click();
    expect(onSelectProject).toHaveBeenCalledWith(1);
  });
});
