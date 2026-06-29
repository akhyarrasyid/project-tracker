import "@testing-library/jest-dom";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { issueApi } from "./api/issues";
import { metaApi } from "./api/meta";
import { projectApi } from "./api/projects";
import { taskApi } from "./api/tasks";
import { queryClient } from "./app/query-client";

vi.mock("./api/meta", () => ({
  metaApi: {
    getDepartments: vi.fn(() => Promise.resolve([])),
    getTeams: vi.fn(() => Promise.resolve([])),
    getProjects: vi.fn(),
    getUsers: vi.fn(() => Promise.resolve([])),
  },
}));

vi.mock("./api/tasks", () => ({
  taskApi: {
    getAll: vi.fn(),
    getById: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock("./api/projects", () => ({
  projectApi: {
    getSummary: vi.fn(),
  },
}));

vi.mock("./api/issues", () => ({
  issueApi: {
    getByKey: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock("./contexts/AuthContext", () => ({
  AuthProvider: ({ children }: { children: ReactNode }) => children,
  useAuth: () => ({
    user: {
      id: 7,
      username: "admin",
      full_name: "Administrator",
      role: "admin",
      team_id: 1,
    },
    loading: false,
    login: vi.fn(),
    logout: vi.fn(),
  }),
}));

const projects = [
  {
    id: 1,
    name: "Payment Platform",
    key: "PAY",
    status: "ACTIVE",
    description: "Payments",
  },
  {
    id: 2,
    name: "Compliance 2026",
    key: "COM",
    status: "ACTIVE",
    description: "Compliance",
  },
];

const boardResponse = {
  items: [
    {
      id: 12,
      number: 12,
      key: "PAY-12",
      project_key: "PAY",
      project_id: 1,
      assignee_id: 7,
      title: "Handle duplicate callback",
      description: "Investigate duplicate payment callback",
      status: "Todo" as const,
      is_blocked: false,
      blocked_reason: null,
      priority: "High" as const,
      department: "Engineering",
      team: "Backend Team",
      assignee: "Administrator",
      created_by: "admin",
      created_at: "2026-06-29T00:00:00Z",
      updated_at: "2026-06-29T00:00:00Z",
      due_date: "2026-07-05",
      completed_at: null,
      story_points: 3,
      estimated_hours: 8,
      actual_hours: 0,
      progress_percentage: 0,
      attachments_count: 0,
      comments_count: 0,
      watchers_count: 0,
      sprint: null,
      quarter: "Q3" as const,
      risk_level: "Low" as const,
      customer_impact: "High" as const,
      sla_hours: 48,
      dependencies: [],
      tags: ["payments"],
    },
  ],
  total: 1,
  page: 1,
  size: 20,
  pages: 1,
};

const projectSummary = {
  total_issues: 14,
  done_issues: 5,
  active_issues: 9,
  issue_progress_percent: 36,
  point_progress_percent: 33,
  blocked_count: 2,
  overdue_count: 1,
  at_risk_count: 3,
};

beforeEach(() => {
  vi.clearAllMocks();
  queryClient.clear();
  window.history.replaceState({}, "", "/");

  vi.mocked(metaApi.getProjects).mockResolvedValue(projects);
  vi.mocked(taskApi.getAll).mockResolvedValue(boardResponse);
  vi.mocked(projectApi.getSummary).mockResolvedValue(projectSummary);
  vi.mocked(issueApi.getByKey).mockResolvedValue(boardResponse.items[0]);
});

describe("Milestone 2 frontend foundation", () => {
  it("routes project pages by projectKey", async () => {
    window.history.replaceState({}, "", "/projects/PAY/board");

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Payment Platform" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Board view")).toBeInTheDocument();
    await waitFor(() => {
      expect(vi.mocked(taskApi.getAll)).toHaveBeenCalledWith({
        project_id: 1,
        page: 1,
        size: 20,
      });
    });
  });

  it("supports issue deep-link by issueKey", async () => {
    window.history.replaceState({}, "", "/issues/PAY-12");

    render(<App />);

    expect(await screen.findByText("PAY-12")).toBeInTheDocument();
    expect(screen.getByText("Handle duplicate callback")).toBeInTheDocument();
    expect(vi.mocked(issueApi.getByKey)).toHaveBeenCalledWith("PAY-12");
  });

  it("shares project query cache across sidebar and project layout", async () => {
    window.history.replaceState({}, "", "/projects/PAY/board");

    render(<App />);

    await screen.findByRole("heading", { name: "Payment Platform" });

    await waitFor(() => {
      expect(vi.mocked(metaApi.getProjects)).toHaveBeenCalledTimes(1);
    });
  });

  it("preserves the active page on refresh via browser route", async () => {
    window.history.replaceState({}, "", "/projects/PAY/calendar");

    render(<App />);

    expect(await screen.findByText("Calendar view")).toBeInTheDocument();
    expect(screen.getByText("Senin")).toBeInTheDocument();
  });
});
