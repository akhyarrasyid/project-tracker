import { describe, expect, it } from "vitest";

import { applyOptimisticMove, removeTaskFromBoard } from "./board-cache";
import type { BoardResponse, Task } from "../../types/task";

function createTask(id: number, status: Task["status"], rank: number): Task {
  return {
    id,
    number: id,
    rank,
    version: 1,
    key: `PAY-${id}`,
    project_id: 1,
    project_key: "PAY",
    parent_id: null,
    title: `Task ${id}`,
    description: "",
    status,
    is_blocked: false,
    priority: "Medium",
    created_at: "2026-06-29T00:00:00Z",
    updated_at: "2026-06-29T00:00:00Z",
    due_date: "2026-07-01",
    completed_at: null,
    story_points: 3,
    estimated_hours: 8,
    actual_hours: 0,
    progress_percentage: 0,
    attachments_count: 0,
    comments_count: 0,
    watchers_count: 0,
    quarter: "Q3",
    risk_level: "Low",
    customer_impact: "None",
    sla_hours: 48,
    dependencies: [],
    tags: [],
  };
}

function createBoard(): BoardResponse {
  return {
    columns: {
      Todo: {
        status: "Todo",
        items: [createTask(1, "Todo", 1024), createTask(2, "Todo", 2048)],
        total_count: 2,
      },
      "In Progress": {
        status: "In Progress",
        items: [createTask(3, "In Progress", 1024)],
        total_count: 1,
      },
      Review: { status: "Review", items: [], total_count: 0 },
      Done: { status: "Done", items: [], total_count: 0 },
    },
  };
}

describe("board cache helpers", () => {
  it("optimistically reorders issues between columns", () => {
    const board = createBoard();
    const moved = applyOptimisticMove(board, board.columns["In Progress"].items[0], {
      status: "Todo",
      after_issue_id: 1,
      before_issue_id: 2,
    });

    expect(moved.columns.Todo.items.map((item) => item.id)).toEqual([1, 3, 2]);
    expect(moved.columns["In Progress"].items).toHaveLength(0);
  });

  it("removes deleted issues and decrements the source count", () => {
    const board = createBoard();
    const nextBoard = removeTaskFromBoard(board, 2);

    expect(nextBoard.columns.Todo.items.map((item) => item.id)).toEqual([1]);
    expect(nextBoard.columns.Todo.total_count).toBe(1);
  });
});
