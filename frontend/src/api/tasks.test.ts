import { describe, it, expect, vi } from "vitest";
import { taskApi } from "./tasks";
import axios from "axios";

vi.mock("axios", () => {
  const mockAxiosInstance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  };
  return {
    default: {
      create: vi.fn(() => mockAxiosInstance),
    },
  };
});

describe("taskApi", () => {
  it("should make GET request to /tasks/", async () => {
    const mockData = [{ id: 1, title: "Test Task" }];
    const instance = axios.create();
    vi.mocked(instance.get).mockResolvedValueOnce({ data: mockData });

    const result = await taskApi.getAll();
    expect(instance.get).toHaveBeenCalledWith("/tasks/");
    expect(result).toEqual(mockData);
  });

  it("should make POST request to /tasks/", async () => {
    const mockData = { id: 1, title: "New Task" };
    const instance = axios.create();
    vi.mocked(instance.post).mockResolvedValueOnce({ data: mockData });

    const result = await taskApi.create({ title: "New Task" } as any);
    expect(instance.post).toHaveBeenCalledWith("/tasks/", { title: "New Task" });
    expect(result).toEqual(mockData);
  });

  it("should make PUT request to /tasks/:id", async () => {
    const mockData = { id: 1, title: "Updated Task" };
    const instance = axios.create();
    vi.mocked(instance.put).mockResolvedValueOnce({ data: mockData });

    const result = await taskApi.update(1, { title: "Updated Task" } as any);
    expect(instance.put).toHaveBeenCalledWith("/tasks/1", { title: "Updated Task" });
    expect(result).toEqual(mockData);
  });

  it("should make DELETE request to /tasks/:id", async () => {
    const instance = axios.create();
    vi.mocked(instance.delete).mockResolvedValueOnce({ data: {} });

    await taskApi.delete(1);
    expect(instance.delete).toHaveBeenCalledWith("/tasks/1");
  });
});
