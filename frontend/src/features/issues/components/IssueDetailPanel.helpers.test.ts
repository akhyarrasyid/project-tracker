import { describe, expect, it } from "vitest";

import {
  describeActivity,
  getConflictMessage,
  getLatestIssue,
  getRequestErrorMessage,
} from "./issue-detail-helpers";
import type { IssueActivity, Task } from "../../../types/task";

const latestIssue = {
  id: 88,
  key: "PAY-88",
  title: "Updated elsewhere",
} as Task;

describe("IssueDetailPanel helpers", () => {
  it("formats activity descriptions for changed fields and generic actions", () => {
    const changed: IssueActivity = {
      id: 1,
      action: "updated",
      field: "status",
      old_value: "Todo",
      new_value: "Review",
      created_at: "2026-07-01T01:00:00Z",
      actor: { id: 2, username: "amanda", full_name: "Amanda" },
    };

    const created: IssueActivity = {
      id: 2,
      action: "created",
      field: null,
      old_value: null,
      new_value: null,
      created_at: "2026-07-01T01:00:00Z",
      actor: { id: 3, username: "dinda", full_name: "Dinda" },
    };

    const updated: IssueActivity = {
      id: 3,
      action: "updated",
      field: "blocked_reason",
      old_value: null,
      new_value: "Waiting for security review",
      created_at: "2026-07-01T01:00:00Z",
      actor: { id: 4, username: "rio", full_name: "Rio" },
    };

    expect(describeActivity(changed)).toBe("Amanda changed status from Todo to Review");
    expect(describeActivity(created)).toBe("Dinda created");
    expect(describeActivity(updated)).toBe(
      "Rio updated blocked_reason to Waiting for security review",
    );
  });

  it("extracts conflict and latest issue details from API errors", () => {
    const error = {
      response: {
        data: {
          detail: {
            message: "Issue version is stale",
            latest_issue: latestIssue,
          },
        },
      },
    };

    expect(getConflictMessage(error)).toBe("Issue version is stale");
    expect(getLatestIssue(error)).toBe(latestIssue);
    expect(getConflictMessage({})).toBeNull();
    expect(getLatestIssue({})).toBeNull();
  });

  it("maps request errors to friendly delete feedback", () => {
    expect(
      getRequestErrorMessage(
        { response: { status: 403, data: { detail: "Viewer cannot delete issues" } } },
        "fallback",
      ),
    ).toBe("Viewer cannot delete issues");
    expect(getRequestErrorMessage({ response: { status: 404, data: {} } }, "fallback")).toBe(
      "Issue ini sudah tidak tersedia atau sudah dihapus.",
    );
    expect(getRequestErrorMessage({ response: { status: 500, data: {} } }, "fallback")).toBe(
      "fallback",
    );
    expect(getRequestErrorMessage({ response: { status: 403, data: {} } }, "fallback")).toBe(
      "Akun ini tidak punya izin untuk menghapus issue.",
    );
  });
});
