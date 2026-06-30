import "@testing-library/jest-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { notificationApi } = vi.hoisted(() => ({
  notificationApi: {
    markRead: vi.fn(),
    markUnread: vi.fn(),
    markAllRead: vi.fn(),
  },
}));

vi.mock("../../../api/notifications", () => ({
  notificationApi,
}));

import { queryClient } from "../../../app/query-client";
import type { NotificationItem, NotificationListResponse } from "../../../types/notification";
import { notificationKeys } from "./queryKeys";
import {
  useMarkAllNotificationsReadMutation,
  useMarkNotificationReadMutation,
  useMarkNotificationUnreadMutation,
} from "./useNotificationMutations";

const baseNotification: NotificationItem = {
  id: 1,
  type: "issue_assigned",
  title: "Amanda assigned you to PAY-12",
  body_preview: "Handle duplicate callback",
  metadata: {},
  is_read: false,
  read_at: null,
  created_at: "2026-06-30T10:00:00Z",
  actor: { id: 1, username: "amanda", full_name: "Amanda" },
  issue: { id: 12, key: "PAY-12", title: "Handle duplicate callback" },
  project: { id: 1, key: "PAY", name: "Payment Platform" },
  route_target: "/issues/PAY-12",
};

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

function seedNotifications(items: NotificationItem[]) {
  queryClient.setQueryData(notificationKeys.list("all", null, 20), {
    pages: [{ items, next_cursor: null } satisfies NotificationListResponse],
    pageParams: [null],
  });
}

describe("notification mutations", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("marks a notification as read and keeps the cache synced", async () => {
    notificationApi.markRead.mockResolvedValue({ notification: { ...baseNotification, is_read: true, read_at: "now" } });
    seedNotifications([baseNotification]);

    const { result } = renderHook(() => useMarkNotificationReadMutation(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync(1);
    });

    const cached = queryClient.getQueryData<any>(notificationKeys.list("all", null, 20));
    expect(cached.pages[0].items[0].is_read).toBe(true);
    await waitFor(() => {
      expect(notificationApi.markRead).toHaveBeenCalledWith(1);
    });
  });

  it("restores the unread state when mark read fails", async () => {
    notificationApi.markRead.mockRejectedValue(new Error("boom"));
    seedNotifications([baseNotification]);

    const { result } = renderHook(() => useMarkNotificationReadMutation(), { wrapper });

    await expect(result.current.mutateAsync(1)).rejects.toThrow("boom");

    const cached = queryClient.getQueryData<any>(notificationKeys.list("all", null, 20));
    expect(cached.pages[0].items[0].is_read).toBe(false);
  });

  it("marks notifications unread and marks all as read", async () => {
    notificationApi.markUnread.mockResolvedValue({ notification: { ...baseNotification, is_read: false, read_at: null } });
    notificationApi.markAllRead.mockResolvedValue({ updated_count: 1 });
    seedNotifications([{ ...baseNotification, is_read: true, read_at: "now" }]);

    const unreadHook = renderHook(() => useMarkNotificationUnreadMutation(), { wrapper });
    const bulkHook = renderHook(() => useMarkAllNotificationsReadMutation(), { wrapper });

    await act(async () => {
      await unreadHook.result.current.mutateAsync(1);
      await bulkHook.result.current.mutateAsync();
    });

    const cached = queryClient.getQueryData<any>(notificationKeys.list("all", null, 20));
    expect(cached.pages[0].items[0].is_read).toBe(true);
    expect(notificationApi.markUnread).toHaveBeenCalledWith(1);
    expect(notificationApi.markAllRead).toHaveBeenCalledTimes(1);
  });
});
