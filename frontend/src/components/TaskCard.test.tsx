import "@testing-library/jest-dom";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TaskCard } from "./TaskCard";
import type { Task } from "../types/task";

const baseTask: Task = {
  id: 91,
  project_id: 1,
  project_key: "PAY",
  key: "PAY-91",
  number: 91,
  title: "Add reconciliation report export",
  description: "Export finance reconciliation data.",
  status: "Todo",
  priority: "Medium",
  assignee_id: null,
  assignee: null,
  created_by_id: 1,
  created_by: "Demo Admin",
  due_date: "2026-07-07T00:00:00Z",
  estimated_hours: 12,
  actual_hours: 0,
  story_points: 3,
  quarter: "Q3",
  risk_level: "Low",
  customer_impact: "Medium",
  sla_hours: 48,
  progress_percentage: 0,
  is_blocked: false,
  blocked_reason: null,
  sprint_id: 1,
  sprint: "Sprint 12",
  epic_id: 1,
  parent_id: null,
  rank: 1,
  version: 2,
  tags: ["reporting", "finance", "ignored-third-tag"],
  dependencies: [],
  comments_count: 4,
  attachments_count: 1,
  watchers_count: 3,
  created_at: "2026-06-19T07:00:00Z",
  updated_at: "2026-06-28T15:00:00Z",
  completed_at: null,
  department: "Finance",
  team: "Revenue Operations",
};

describe("TaskCard", () => {
  it("renders key details, limits visible tags, and opens the issue on click", () => {
    const onTaskClick = vi.fn();
    render(<TaskCard task={baseTask} onTaskClick={onTaskClick} />);

    expect(screen.getByText("PAY-91")).toBeInTheDocument();
    expect(screen.getByText("Medium")).toBeInTheDocument();
    expect(screen.getByText("Add reconciliation report export")).toBeInTheDocument();
    expect(screen.getByText("reporting")).toBeInTheDocument();
    expect(screen.getByText("finance")).toBeInTheDocument();
    expect(screen.queryByText("ignored-third-tag")).not.toBeInTheDocument();
    expect(screen.getByText("Unassigned")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button"));
    expect(onTaskClick).toHaveBeenCalledWith(baseTask);
  });

  it("shows blocked state and assignee when the issue is blocked", () => {
    render(
      <TaskCard
        task={{
          ...baseTask,
          assignee: "Rio Fernando",
          is_blocked: true,
          priority: "Critical",
          status: "Review",
          tags: [],
        }}
        onTaskClick={vi.fn()}
      />,
    );

    expect(screen.getByText("Blocked")).toBeInTheDocument();
    expect(screen.getByText("Rio Fernando")).toBeInTheDocument();
    expect(screen.queryByText("reporting")).not.toBeInTheDocument();
  });
});
