import { beforeEach, describe, expect, it, vi } from "vitest";

const { client } = vi.hoisted(() => ({
  client: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock("./client", () => ({
  default: client,
}));

import { authApi } from "./auth";
import { issueApi } from "./issues";
import { metaApi } from "./meta";
import { notificationApi } from "./notifications";
import { projectApi } from "./projects";

describe("API modules", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("submits login form data and fetches the current user", async () => {
    client.post.mockResolvedValueOnce({ data: { access_token: "a", refresh_token: "b", token_type: "bearer" } });
    client.get.mockResolvedValueOnce({ data: { id: 1, username: "admin" } });

    await expect(authApi.login("admin", "secret")).resolves.toEqual({
      access_token: "a",
      refresh_token: "b",
      token_type: "bearer",
    });
    await expect(authApi.getMe()).resolves.toEqual({ id: 1, username: "admin" });

    expect(client.post).toHaveBeenCalledWith(
      "/api/v1/auth/login",
      expect.any(URLSearchParams),
      expect.objectContaining({
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      }),
    );
    expect(client.get).toHaveBeenCalledWith("/api/v1/auth/me");
  });

  it("calls issue endpoints with the expected routes", async () => {
    client.get.mockResolvedValue({ data: { id: 10 } });
    client.put.mockResolvedValue({ data: { id: 10 } });
    client.patch.mockResolvedValue({ data: { id: 10 } });
    client.post.mockResolvedValue({ data: { id: 10 } });
    client.delete.mockResolvedValue({ data: undefined });

    await issueApi.getByKey("PAY-10");
    await issueApi.update("PAY-10", { title: "Updated" });
    await issueApi.patch(10, { expected_version: 3 });
    await issueApi.move(10, { status: "Done", expected_version: 3 });
    await issueApi.getComments(10);
    await issueApi.createComment(10, "Hello", 2);
    await issueApi.getActivities(10);
    await issueApi.getWatchers(10);
    await issueApi.watchMe(10);
    await issueApi.unwatchMe(10);
    await issueApi.deleteById(10);
    await issueApi.delete("PAY-10");

    expect(client.get).toHaveBeenCalledWith("/api/v1/issues/PAY-10");
    expect(client.put).toHaveBeenCalledWith("/api/v1/issues/PAY-10", { title: "Updated" });
    expect(client.patch).toHaveBeenCalledWith("/api/v1/issues/10", { expected_version: 3 });
    expect(client.patch).toHaveBeenCalledWith("/api/v1/issues/10/move", { status: "Done", expected_version: 3 });
    expect(client.get).toHaveBeenCalledWith("/api/v1/issues/10/comments");
    expect(client.post).toHaveBeenCalledWith("/api/v1/issues/10/comments", { content: "Hello", parent_id: 2 });
    expect(client.get).toHaveBeenCalledWith("/api/v1/issues/10/activities");
    expect(client.get).toHaveBeenCalledWith("/api/v1/issues/10/watchers");
    expect(client.post).toHaveBeenCalledWith("/api/v1/issues/10/watchers/me");
    expect(client.delete).toHaveBeenCalledWith("/api/v1/issues/10/watchers/me");
    expect(client.delete).toHaveBeenCalledWith("/api/v1/issues/10");
    expect(client.delete).toHaveBeenCalledWith("/api/v1/issues/PAY-10");
  });

  it("builds meta queries with optional filters", async () => {
    client.get.mockResolvedValue({ data: [] });

    await metaApi.getDepartments();
    await metaApi.getTeams();
    await metaApi.getTeams(9);
    await metaApi.getProjects();
    await metaApi.getProjects(5);
    await metaApi.getUsers();
    await metaApi.getUsers(7);

    expect(client.get).toHaveBeenCalledWith("/api/v1/meta/departments");
    expect(client.get).toHaveBeenCalledWith("/api/v1/meta/teams", { params: {} });
    expect(client.get).toHaveBeenCalledWith("/api/v1/meta/teams", { params: { department_id: 9 } });
    expect(client.get).toHaveBeenCalledWith("/api/v1/meta/projects", { params: {} });
    expect(client.get).toHaveBeenCalledWith("/api/v1/meta/projects", { params: { team_id: 5 } });
    expect(client.get).toHaveBeenCalledWith("/api/v1/meta/users", { params: {} });
    expect(client.get).toHaveBeenCalledWith("/api/v1/meta/users", { params: { project_id: 7 } });
  });

  it("builds notification endpoints and query strings", async () => {
    client.get.mockResolvedValue({ data: { items: [], next_cursor: null } });
    client.patch.mockResolvedValue({ data: { notification: { id: 1 } } });
    client.post.mockResolvedValue({ data: { updated_count: 1 } });

    await notificationApi.list({ filter: "mentions", cursor: "abc", limit: 10, projectId: 2 });
    await notificationApi.getUnreadCount();
    await notificationApi.getUnreadCount(2);
    await notificationApi.markRead(3);
    await notificationApi.markUnread(4);
    await notificationApi.markAllRead();

    expect(client.get).toHaveBeenCalledWith(
      "/api/v1/notifications?filter=mentions&cursor=abc&limit=10&project_id=2",
    );
    expect(client.get).toHaveBeenCalledWith("/api/v1/notifications/unread-count");
    expect(client.get).toHaveBeenCalledWith("/api/v1/notifications/unread-count?project_id=2");
    expect(client.patch).toHaveBeenCalledWith("/api/v1/notifications/3/read");
    expect(client.patch).toHaveBeenCalledWith("/api/v1/notifications/4/unread");
    expect(client.post).toHaveBeenCalledWith("/api/v1/notifications/mark-all-read");
  });

  it("calls project summary and board endpoints", async () => {
    client.get.mockResolvedValue({ data: { id: 1 } });

    await projectApi.getSummary(8);
    await projectApi.getBoard(8, { limit: 50, start: true });

    expect(client.get).toHaveBeenCalledWith("/api/v1/projects/8/summary");
    expect(client.get).toHaveBeenCalledWith("/api/v1/projects/8/board", {
      params: { limit: 50, start: true },
    });
  });
});
