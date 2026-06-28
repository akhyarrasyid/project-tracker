import { describe, it, expect, vi } from "vitest";
import client from "./client";
import { taskApi } from "./tasks";

vi.mock("./client", () => {
  return {
    default: {
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      delete: vi.fn(),
    },
  };
});

describe("taskApi", () => {
  it("getAll calls /api/v1/tasks/ with params", async () => {
    const resp = { items: [], total: 0, page: 1, size: 20, pages: 0 };
    vi.mocked(client.get).mockResolvedValueOnce({ data: resp });
    const result = await taskApi.getAll({ page: 1, size: 20 });
    expect(client.get).toHaveBeenCalledWith("/api/v1/tasks/", { params: { page: 1, size: 20 } });
    expect(result).toEqual(resp);
  });

  it("getAll calls without params", async () => {
    const resp = { items: [], total: 0, page: 1, size: 20, pages: 0 };
    vi.mocked(client.get).mockResolvedValueOnce({ data: resp });
    await taskApi.getAll();
    expect(client.get).toHaveBeenCalledWith("/api/v1/tasks/", { params: undefined });
  });

  it("getById calls /api/v1/tasks/:id", async () => {
    const task = { id: 1, title: "T" };
    vi.mocked(client.get).mockResolvedValueOnce({ data: task });
    const result = await taskApi.getById(1);
    expect(client.get).toHaveBeenCalledWith("/api/v1/tasks/1");
    expect(result).toEqual(task);
  });

  it("create posts to /api/v1/tasks/ with project_id", async () => {
    const task = { id: 1, title: "New" };
    vi.mocked(client.post).mockResolvedValueOnce({ data: task });
    const result = await taskApi.create({ title: "New" } as any, 10);
    expect(client.post).toHaveBeenCalledWith("/api/v1/tasks/?project_id=10", { title: "New" });
    expect(result).toEqual(task);
  });

  it("update puts to /api/v1/tasks/:id", async () => {
    const task = { id: 1, title: "Updated" };
    vi.mocked(client.put).mockResolvedValueOnce({ data: task });
    const result = await taskApi.update(1, { title: "Updated" } as any);
    expect(client.put).toHaveBeenCalledWith("/api/v1/tasks/1", { title: "Updated" });
    expect(result).toEqual(task);
  });

  it("delete calls /api/v1/tasks/:id", async () => {
    vi.mocked(client.delete).mockResolvedValueOnce({ data: {} });
    await taskApi.delete(1);
    expect(client.delete).toHaveBeenCalledWith("/api/v1/tasks/1");
  });
});
