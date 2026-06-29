import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { issueApi } from "../../../api/issues";
import { metaApi } from "../../../api/meta";
import { taskApi } from "../../../api/tasks";
import { queryClient } from "../../../app/query-client";
import { AppProviders } from "../../../app/providers";
import type { IssueActivity, IssueComment, Task } from "../../../types/task";
import { IssueDetailPanel } from "./IssueDetailPanel";

vi.mock("../../../contexts/AuthContext", () => ({
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

vi.mock("../../../api/issues", () => ({
  issueApi: {
    getByKey: vi.fn(),
    patch: vi.fn(),
    update: vi.fn(),
    move: vi.fn(),
    getComments: vi.fn(),
    createComment: vi.fn(),
    getActivities: vi.fn(),
    deleteById: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock("../../../api/meta", () => ({
  metaApi: {
    getDepartments: vi.fn(),
    getTeams: vi.fn(),
    getProjects: vi.fn(),
    getUsers: vi.fn(),
  },
}));

vi.mock("../../../api/tasks", () => ({
  taskApi: {
    getAll: vi.fn(),
    getById: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
  },
}));

const baseIssue: Task = {
  id: 12,
  number: 12,
  rank: 1024,
  version: 1,
  key: "PAY-12",
  project_key: "PAY",
  project_id: 1,
  sprint_id: null,
  epic_id: null,
  assignee_id: 7,
  parent_id: null,
  title: "Handle duplicate callback",
  description: "Investigate duplicate payment callback",
  status: "Todo",
  is_blocked: false,
  blocked_reason: null,
  priority: "High",
  department: "Engineering",
  team: "Platform",
  assignee: "Administrator",
  created_by: "admin",
  created_by_id: 7,
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
  sprint: "Sprint 4",
  quarter: "Q3",
  risk_level: "Low",
  customer_impact: "High",
  sla_hours: 48,
  dependencies: [],
  tags: ["payments", "backend"],
};

const baseActivities: IssueActivity[] = [];
const baseComments: IssueComment[] = [];

function renderPanel() {
  return render(
    <AppProviders>
      <IssueDetailPanel issueKey="PAY-12" mode="page" />
    </AppProviders>,
  );
}

beforeEach(() => {
  queryClient.clear();
  vi.clearAllMocks();
  queryClient.setQueryData(["issue", "PAY-12"], baseIssue);

  vi.mocked(issueApi.getByKey).mockResolvedValue(baseIssue);
  vi.mocked(issueApi.patch).mockResolvedValue(baseIssue);
  vi.mocked(issueApi.getComments).mockResolvedValue(baseComments);
  vi.mocked(issueApi.getActivities).mockResolvedValue(baseActivities);
  vi.mocked(issueApi.createComment).mockResolvedValue({
    id: 91,
    task_id: 12,
    author_id: 7,
    content: "Please verify callback retries.",
    parent_id: null,
    created_at: "2026-06-29T10:00:00Z",
    updated_at: "2026-06-29T10:00:00Z",
    author: {
      id: 7,
      username: "admin",
      full_name: "Administrator",
    },
  });
  vi.mocked(issueApi.deleteById).mockResolvedValue({ data: undefined } as never);
  vi.mocked(metaApi.getUsers).mockResolvedValue([
    { id: 7, full_name: "Administrator", email: "admin@tracker.com" },
    { id: 10, full_name: "Amanda", email: "amanda@tracker.com" },
  ]);
  vi.mocked(taskApi.getAll).mockResolvedValue({
    items: [
      baseIssue,
      {
        ...baseIssue,
        id: 22,
        number: 22,
        key: "PAY-22",
        parent_id: 12,
        title: "Retry reconciliation job",
      },
    ],
    total: 2,
    page: 1,
    size: 100,
    pages: 1,
  });
});

describe("IssueDetailPanel", () => {
  it("renders issue detail with more properties collapsed by default", async () => {
    renderPanel();

    expect(await screen.findByLabelText("Issue title")).toHaveValue("Handle duplicate callback");
    expect(screen.getByText("PAY-12")).toBeInTheDocument();
    expect(screen.queryByText("Risk level")).not.toBeInTheDocument();
  });

  it("autosaves priority changes with expected version", async () => {
    vi.mocked(issueApi.patch).mockResolvedValueOnce({
      ...baseIssue,
      priority: "Critical",
      version: 2,
    });

    renderPanel();
    fireEvent.change(await screen.findByLabelText("Issue priority"), {
      target: { value: "Critical" },
    });

    await waitFor(() => {
      expect(vi.mocked(issueApi.patch)).toHaveBeenCalledWith(
        12,
        expect.objectContaining({
          priority: "Critical",
          expected_version: 1,
        }),
      );
    });
    expect(await screen.findByText("Saved")).toBeInTheDocument();
  });

  it("shows conflict warning and refreshes latest issue after 409", async () => {
    vi.mocked(issueApi.patch).mockRejectedValueOnce({
      response: {
        status: 409,
        data: {
          detail: {
            message: "Issue version is stale",
            latest_issue: {
              ...baseIssue,
              version: 3,
              title: "Updated elsewhere",
            },
          },
        },
      },
    });

    renderPanel();
    fireEvent.change(await screen.findByLabelText("Issue priority"), {
      target: { value: "Critical" },
    });

    expect(await screen.findByText("Issue version is stale")).toBeInTheDocument();
    expect(await screen.findByLabelText("Issue title")).toHaveValue("Updated elsewhere");
  });

  it("creates comments and refreshes activity queries", async () => {
    renderPanel();

    fireEvent.change(await screen.findByLabelText("New comment"), {
      target: { value: "Please verify callback retries." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Post comment" }));

    await waitFor(() => {
      expect(vi.mocked(issueApi.createComment)).toHaveBeenCalledWith(
        12,
        "Please verify callback retries.",
      );
    });
    expect(await screen.findByText("Please verify callback retries.")).toBeInTheDocument();
  });

  it("deletes only through overflow menu with custom dialog", async () => {
    const confirmSpy = vi.spyOn(window, "confirm");
    renderPanel();

    fireEvent.click(await screen.findByLabelText("Issue actions"));
    fireEvent.click(screen.getByRole("button", { name: "Delete issue" }));

    expect(screen.getByText("Delete issue?")).toBeInTheDocument();
    expect(confirmSpy).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    await waitFor(() => {
      expect(vi.mocked(issueApi.deleteById)).toHaveBeenCalledWith(12);
    });
    confirmSpy.mockRestore();
  });
});
