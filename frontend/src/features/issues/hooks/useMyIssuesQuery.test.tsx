import "@testing-library/jest-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { getAll } = vi.hoisted(() => ({
  getAll: vi.fn(),
}));

vi.mock("../../../api/tasks", () => ({
  taskApi: {
    getAll,
  },
}));

import { queryClient } from "../../../app/query-client";
import { useMyIssuesQuery } from "./useMyIssuesQuery";

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

describe("useMyIssuesQuery", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("stays idle without a user id", () => {
    const { result } = renderHook(() => useMyIssuesQuery(), { wrapper });

    expect(result.current.fetchStatus).toBe("idle");
    expect(getAll).not.toHaveBeenCalled();
  });

  it("loads assigned issues for the active user", async () => {
    getAll.mockResolvedValue({ items: [], total: 0, page: 1, size: 20, pages: 0 });

    const { result } = renderHook(() => useMyIssuesQuery(7), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
    expect(getAll).toHaveBeenCalledWith({
      assignee_id: 7,
      page: 1,
      size: 20,
      sort_by: "due_date",
      sort_order: "asc",
    });
  });
});
