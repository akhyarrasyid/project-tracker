import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  buildMoveInput,
  filterNotifications,
  findTask,
  getGroupLabel,
  getRelativeTimeLabel,
  groupNotifications,
} from "./route-helpers";
import type { NotificationItem } from "../types/notification";
import type { BoardResponse } from "../types/task";

const board: BoardResponse = {
  columns: {
    Todo: {
      status: "Todo",
      total_count: 2,
      items: [
        { id: 1, key: "PAY-1", title: "Todo 1", status: "Todo", version: 1 } as never,
        { id: 2, key: "PAY-2", title: "Todo 2", status: "Todo", version: 1 } as never,
      ],
    },
    "In Progress": {
      status: "In Progress",
      total_count: 2,
      items: [
        { id: 3, key: "PAY-3", title: "Doing 1", status: "In Progress", version: 1 } as never,
        { id: 4, key: "PAY-4", title: "Doing 2", status: "In Progress", version: 1 } as never,
      ],
    },
    Review: {
      status: "Review",
      total_count: 0,
      items: [],
    },
    Done: {
      status: "Done",
      total_count: 0,
      items: [],
    },
  },
};

const notifications: NotificationItem[] = [
  {
    id: 1,
    type: "issue_assigned",
    title: "Amanda assigned you to PAY-12",
    body_preview: "Handle duplicate callback",
    metadata: {},
    is_read: false,
    read_at: null,
    created_at: "2026-07-01T01:00:00Z",
    actor: { id: 1, username: "amanda", full_name: "Amanda Putri" },
    issue: { id: 12, key: "PAY-12", title: "Handle duplicate callback" },
    project: { id: 1, key: "PAY", name: "Payment Platform" },
    route_target: "/issues/PAY-12",
  },
  {
    id: 2,
    type: "issue_mentioned",
    title: "Dinda mentioned you in IAM-14",
    body_preview: "Please verify the retention update.",
    metadata: {},
    is_read: true,
    read_at: "2026-07-01T00:00:00Z",
    created_at: "2026-06-30T01:00:00Z",
    actor: { id: 2, username: "dinda", full_name: "Dinda Maharani" },
    issue: { id: 14, key: "IAM-14", title: "Retention update" },
    project: { id: 2, key: "IAM", name: "Identity & Access" },
    route_target: "/issues/IAM-14",
  },
];

describe("route helpers", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-07-01T08:00:00Z"));
  });

  it("finds tasks across board columns", () => {
    expect(findTask(board, 4)?.key).toBe("PAY-4");
    expect(findTask(board, 999)).toBeNull();
  });

  it("builds move input for column drops and task reorder drops", () => {
    expect(buildMoveInput(board, 1, "column:Review")).toEqual({
      status: "Review",
      after_issue_id: null,
    });

    expect(buildMoveInput(board, 4, "task:3")).toEqual({
      status: "In Progress",
      before_issue_id: 3,
      after_issue_id: null,
    });

    expect(buildMoveInput(board, 3, "task:4")).toEqual({
      status: "In Progress",
      before_issue_id: 4,
      after_issue_id: null,
    });
  });

  it("returns null for unsupported move targets", () => {
    expect(buildMoveInput(board, 1, "swimlane:foo")).toBeNull();
    expect(buildMoveInput(board, 1, "task:999")).toBeNull();
  });

  it("filters and groups notifications with relative time labels", () => {
    expect(filterNotifications(notifications, "dinda")).toEqual([notifications[1]]);
    expect(filterNotifications(notifications, "payment")).toEqual([notifications[0]]);
    expect(filterNotifications(notifications, "")).toHaveLength(2);

    expect(getGroupLabel(notifications[0].created_at)).toBe("Today");
    expect(getGroupLabel(notifications[1].created_at)).toBe("Yesterday");
    expect(getRelativeTimeLabel(notifications[0].created_at)).toContain("hour");

    const groups = groupNotifications(notifications);
    expect(groups).toEqual([
      ["Today", [notifications[0]]],
      ["Yesterday", [notifications[1]]],
    ]);
  });
});
