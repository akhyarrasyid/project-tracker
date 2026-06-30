import type { InfiniteData } from "@tanstack/react-query";
import { useMutation } from "@tanstack/react-query";

import { notificationApi } from "../../../api/notifications";
import { queryClient } from "../../../app/query-client";
import type { NotificationItem, NotificationListResponse } from "../../../types/notification";
import { notificationKeys } from "./queryKeys";

function updateNotificationLists(
  notificationId: number,
  updater: (notification: NotificationItem) => NotificationItem,
) {
  const snapshots = queryClient.getQueriesData<InfiniteData<NotificationListResponse>>({
    queryKey: notificationKeys.lists(),
  });

  for (const [queryKey, data] of snapshots) {
    if (!data) {
      continue;
    }

    queryClient.setQueryData<InfiniteData<NotificationListResponse>>(queryKey, {
      ...data,
      pages: data.pages.map((page) => ({
        ...page,
        items: page.items.map((item) =>
          item.id === notificationId ? updater(item) : item,
        ),
      })),
    });
  }

  return snapshots;
}

function markAllListsRead() {
  const snapshots = queryClient.getQueriesData<InfiniteData<NotificationListResponse>>({
    queryKey: notificationKeys.lists(),
  });

  const now = new Date().toISOString();
  for (const [queryKey, data] of snapshots) {
    if (!data) {
      continue;
    }

    queryClient.setQueryData<InfiniteData<NotificationListResponse>>(queryKey, {
      ...data,
      pages: data.pages.map((page) => ({
        ...page,
        items: page.items.map((item) => ({
          ...item,
          is_read: true,
          read_at: item.read_at ?? now,
        })),
      })),
    });
  }

  return snapshots;
}

function restoreNotificationSnapshots(
  snapshots: Array<readonly [readonly unknown[], InfiniteData<NotificationListResponse> | undefined]>,
) {
  for (const [queryKey, data] of snapshots) {
    queryClient.setQueryData(queryKey, data);
  }
}

export function useMarkNotificationReadMutation() {
  return useMutation({
    mutationFn: (notificationId: number) => notificationApi.markRead(notificationId),
    onMutate: async (notificationId) => {
      const snapshots = updateNotificationLists(notificationId, (item) => ({
        ...item,
        is_read: true,
        read_at: item.read_at ?? new Date().toISOString(),
      }));
      return { snapshots };
    },
    onError: (_error, _notificationId, context) => {
      if (context?.snapshots) {
        restoreNotificationSnapshots(context.snapshots);
      }
    },
    onSettled: async () => {
      await queryClient.invalidateQueries({ queryKey: notificationKeys.all });
    },
  });
}

export function useMarkNotificationUnreadMutation() {
  return useMutation({
    mutationFn: (notificationId: number) => notificationApi.markUnread(notificationId),
    onMutate: async (notificationId) => {
      const snapshots = updateNotificationLists(notificationId, (item) => ({
        ...item,
        is_read: false,
        read_at: null,
      }));
      return { snapshots };
    },
    onError: (_error, _notificationId, context) => {
      if (context?.snapshots) {
        restoreNotificationSnapshots(context.snapshots);
      }
    },
    onSettled: async () => {
      await queryClient.invalidateQueries({ queryKey: notificationKeys.all });
    },
  });
}

export function useMarkAllNotificationsReadMutation() {
  return useMutation({
    mutationFn: () => notificationApi.markAllRead(),
    onMutate: async () => {
      const snapshots = markAllListsRead();
      return { snapshots };
    },
    onError: (_error, _variables, context) => {
      if (context?.snapshots) {
        restoreNotificationSnapshots(context.snapshots);
      }
    },
    onSettled: async () => {
      await queryClient.invalidateQueries({ queryKey: notificationKeys.all });
    },
  });
}
