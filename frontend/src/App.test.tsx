import "@testing-library/jest-dom";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { issueApi } from "./api/issues";
import { metaApi } from "./api/meta";
import { notificationApi } from "./api/notifications";
import { projectApi } from "./api/projects";
import { queryClient } from "./app/query-client";

vi.mock("./api/meta", () => ({
  metaApi: {
    getDepartments: vi.fn(() => Promise.resolve([])),
    getTeams: vi.fn(() => Promise.resolve([])),
    getProjects: vi.fn(),
    getUsers: vi.fn(() => Promise.resolve([])),
  },
}));

vi.mock("./api/projects", () => ({
  projectApi: {
    getSummary: vi.fn(),
    getBoard: vi.fn(),
  },
}));

vi.mock("./api/notifications", () => ({
  notificationApi: {
    list: vi.fn(),
    getUnreadCount: vi.fn(),
    markRead: vi.fn(),
    markUnread: vi.fn(),
    markAllRead: vi.fn(),
  },
}));

vi.mock("./api/issues", () => ({
  issueApi: {
    getByKey: vi.fn(),
    patch: vi.fn(),
    update: vi.fn(),
    move: vi.fn(),
    getComments: vi.fn(() => Promise.resolve([])),
    createComment: vi.fn(),
    getActivities: vi.fn(() => Promise.resolve([])),
    getWatchers: vi.fn(() => Promise.resolve({ issue_id: 12, count: 0, is_watching: false, can_manage_watchers: true, watchers: [] })),
    watchMe: vi.fn(),
    unwatchMe: vi.fn(),
    deleteById: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock("./api/tasks", () => ({
  taskApi: {
    getAll: vi.fn(() =>
      Promise.resolve({
        items: [],
        total: 0,
        page: 1,
        size: 100,
        pages: 0,
      }),
    ),
    getById: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock("./contexts/AuthContext", () => ({
  AuthProvider: ({ children }: { children: ReactNode }) => children,
}));

vi.mock("./contexts/useAuth", () => ({
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
      rank: 1024,
      version: 1,
      key: "PAY-12",
      project_key: "PAY",
      project_id: 1,
      assignee_id: 7,
      parent_id: null,
      created_by_id: 7,
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
      completed_by_id: null,
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

const notificationsResponse = {
  items: [
    {
      id: 401,
      type: "issue_assigned" as const,
      title: "Amanda assigned you to PAY-12",
      body_preview: "Handle duplicate callback",
      metadata: {},
      is_read: false,
      read_at: null,
      created_at: "2099-06-29T10:00:00Z",
      actor: {
        id: 10,
        username: "amanda",
        full_name: "Amanda",
      },
      issue: {
        id: 12,
        key: "PAY-12",
        title: "Handle duplicate callback",
      },
      project: {
        id: 1,
        key: "PAY",
        name: "Payment Platform",
      },
      route_target: "/issues/PAY-12",
    },
    {
      id: 402,
      type: "issue_commented" as const,
      title: "Dinda commented on PAY-18",
      body_preview: "Please verify callback retries.",
      metadata: {},
      is_read: true,
      read_at: "2099-06-29T11:00:00Z",
      created_at: "2099-06-29T11:00:00Z",
      actor: {
        id: 11,
        username: "dinda",
        full_name: "Dinda",
      },
      issue: {
        id: 18,
        key: "PAY-18",
        title: "Retry callback delivery",
      },
      project: {
        id: 1,
        key: "PAY",
        name: "Payment Platform",
      },
      route_target: "/issues/PAY-18",
    },
  ],
  next_cursor: null,
};

beforeEach(() => {
  vi.clearAllMocks();
  queryClient.clear();
  window.history.replaceState({}, "", "/");

  vi.mocked(metaApi.getProjects).mockResolvedValue(projects);
  vi.mocked(metaApi.getUsers).mockResolvedValue([
    { id: 7, full_name: "Administrator", email: "admin@tracker.com" },
  ]);
  vi.mocked(projectApi.getSummary).mockResolvedValue(projectSummary);
  vi.mocked(projectApi.getBoard).mockResolvedValue({
    columns: {
      Todo: {
        status: "Todo",
        items: boardResponse.items,
        total_count: 1,
      },
      "In Progress": {
        status: "In Progress",
        items: [],
        total_count: 0,
      },
      Review: {
        status: "Review",
        items: [],
        total_count: 0,
      },
      Done: {
        status: "Done",
        items: [],
        total_count: 0,
      },
    },
  });
  vi.mocked(issueApi.getByKey).mockResolvedValue(boardResponse.items[0]);
  vi.mocked(issueApi.patch).mockResolvedValue(boardResponse.items[0]);
  vi.mocked(issueApi.deleteById).mockResolvedValue({ data: undefined } as never);
  vi.mocked(notificationApi.list).mockResolvedValue(notificationsResponse);
  vi.mocked(notificationApi.getUnreadCount).mockResolvedValue({ unread_count: 8 });
  vi.mocked(notificationApi.markRead).mockResolvedValue({
    notification: {
      ...notificationsResponse.items[0],
      is_read: true,
      read_at: "2099-06-29T12:00:00Z",
    },
  });
  vi.mocked(notificationApi.markUnread).mockResolvedValue({
    notification: {
      ...notificationsResponse.items[1],
      is_read: false,
      read_at: null,
    },
  });
  vi.mocked(notificationApi.markAllRead).mockResolvedValue({ updated_count: 8 });
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
      expect(vi.mocked(projectApi.getBoard)).toHaveBeenCalledWith(1, { limit: 50, start: true });
    });
  });

  it("supports issue deep-link by issueKey", async () => {
    window.history.replaceState({}, "", "/issues/PAY-12");

    render(<App />);

    expect(await screen.findByDisplayValue("Handle duplicate callback")).toBeInTheDocument();
    expect(screen.getByText("PAY-12")).toBeInTheDocument();
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

  it("opens and closes the issue sheet from board route context", async () => {
    window.history.replaceState({}, "", "/projects/PAY/board?issue=PAY-12");

    render(<App />);

    expect(await screen.findByDisplayValue("Handle duplicate callback")).toBeInTheDocument();
    expect(window.location.pathname).toBe("/projects/PAY/board");
    expect(window.location.search).toBe("?issue=PAY-12");

    screen.getByLabelText("Close issue").click();

    await waitFor(() => {
      expect(window.location.pathname).toBe("/projects/PAY/board");
      expect(window.location.search).toBe("");
    });
  });

  it("renders inbox with shared unread badge and notification rows", async () => {
    window.history.replaceState({}, "", "/inbox");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Notifications" })).toBeInTheDocument();
    expect(await screen.findByText("8 unread")).toBeInTheDocument();
    expect(screen.getByText("Amanda assigned you to PAY-12")).toBeInTheDocument();
    expect(vi.mocked(notificationApi.getUnreadCount)).toHaveBeenCalledTimes(1);
  });

  it("filters inbox items and opens issue routes from notifications", async () => {
    window.history.replaceState({}, "", "/inbox");

    render(<App />);

    await screen.findByText("Amanda assigned you to PAY-12");

    screen.getByRole("button", { name: "Unread" }).click();
    await waitFor(() => {
      expect(vi.mocked(notificationApi.list)).toHaveBeenLastCalledWith({
        filter: "unread",
        cursor: null,
        limit: 20,
        projectId: null,
      });
    });

    screen.getByRole("button", { name: "Open Amanda assigned you to PAY-12" }).click();

    await waitFor(() => {
      expect(vi.mocked(notificationApi.markRead)).toHaveBeenCalledWith(401);
      expect(window.location.pathname).toBe("/issues/PAY-12");
    });
  });
});
