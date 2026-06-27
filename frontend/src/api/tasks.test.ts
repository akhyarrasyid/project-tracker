import { describe, it, expect, vi } from "vitest";
import axios from "axios";
import { taskApi } from "./tasks";

vi.mock("axios", () => {
  const mockInstance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  };
  return { default: { create: vi.fn(() => mockInstance) } };
});

const inst = axios.create();

describe("taskApi", () => {
  it("getAll calls /api/v1/tasks/ with params", async () => {
    const resp = { items: [], total: 0, page: 1, size: 20, pages: 0 };
    vi.mocked(inst.get).mockResolvedValueOnce({ data: resp });
    const result = await taskApi.getAll({ page: 1, size: 20 });
    expect(inst.get).toHaveBeenCalledWith("/api/v1/tasks/", { params: { page: 1, size: 20 } });
    expect(result).toEqual(resp);
  });

  it("getAll calls without params", async () => {
    const resp = { items: [], total: 0, page: 1, size: 20, pages: 0 };
    vi.mocked(inst.get).mockResolvedValueOnce({ data: resp });
    await taskApi.getAll();
    expect(inst.get).toHaveBeenCalledWith("/api/v1/tasks/", { params: undefined });
  });

  it("getById calls /api/v1/tasks/:id", async () => {
    const task = { id: 1, title: "T" };
    vi.mocked(inst.get).mockResolvedValueOnce({ data: task });
    const result = await taskApi.getById(1);
    expect(inst.get).toHaveBeenCalledWith("/api/v1/tasks/1");
    expect(result).toEqual(task);
  });

  it("create posts to /api/v1/tasks/", async () => {
    const task = { id: 1, title: "New" };
    vi.mocked(inst.post).mockResolvedValueOnce({ data: task });
    const result = await taskApi.create({ title: "New" } as any);
    expect(inst.post).toHaveBeenCalledWith("/api/v1/tasks/", { title: "New" });
    expect(result).toEqual(task);
  });

  it("update puts to /api/v1/tasks/:id", async () => {
    const task = { id: 1, title: "Updated" };
    vi.mocked(inst.put).mockResolvedValueOnce({ data: task });
    const result = await taskApi.update(1, { title: "Updated" } as any);
    expect(inst.put).toHaveBeenCalledWith("/api/v1/tasks/1", { title: "Updated" });
    expect(result).toEqual(task);
  });

  it("delete calls /api/v1/tasks/:id", async () => {
    vi.mocked(inst.delete).mockResolvedValueOnce({ data: {} });
    await taskApi.delete(1);
    expect(inst.delete).toHaveBeenCalledWith("/api/v1/tasks/1");
  });
});
