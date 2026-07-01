import { describe, expect, it } from "vitest";

import { applyOptimisticMove, removeTaskFromBoard } from "./board-cache";
import type { BoardResponse, Task } from "../../types/task";

const todoTask = {
  id: 1,
  key: "PAY-1",
  title: "First",
  status: "Todo",
} as Task;

const progressTask = {
  id: 2,
  key: "PAY-2",
  title: "Second",
  status: "In Progress",
} as Task;

const reviewTask = {
  id: 3,
  key: "PAY-3",
  title: "Third",
  status: "Review",
} as Task;

const board: BoardResponse = {
  columns: {
    Todo: { status: "Todo", items: [todoTask], total_count: 1 },
    "In Progress": {
      status: "In Progress",
      items: [progressTask],
      total_count: 1,
    },
    Review: { status: "Review", items: [reviewTask], total_count: 1 },
    Done: { status: "Done", items: [], total_count: 0 },
  },
};

describe("board-cache", () => {
  it("removes a task from every board column clone", () => {
    const nextBoard = removeTaskFromBoard(board, 2);

    expect(nextBoard.columns["In Progress"].items).toHaveLength(0);
    expect(nextBoard.columns["In Progress"].total_count).toBe(0);
    expect(board.columns["In Progress"].items).toHaveLength(1);
  });

  it("moves tasks before or after another task optimistically", () => {
    const movedBefore = applyOptimisticMove(board, todoTask, {
      status: "Review",
      before_issue_id: 3,
    });
    expect(movedBefore.columns.Review.items.map((task) => task.id)).toEqual([1, 3]);

    const movedAfter = applyOptimisticMove(board, progressTask, {
      status: "Review",
      after_issue_id: 3,
    });
    expect(movedAfter.columns.Review.items.map((task) => task.id)).toEqual([3, 2]);
  });

  it("appends the moved task when no neighbor hint exists", () => {
    const moved = applyOptimisticMove(board, reviewTask, {
      status: "Done",
    });

    expect(moved.columns.Done.items.map((task) => task.id)).toEqual([3]);
    expect(moved.columns.Done.total_count).toBe(1);
  });
});
