export const notificationKeys = {
  all: ["notifications"] as const,
  lists: () => [...notificationKeys.all, "list"] as const,
  list: (filter: string, projectId: number | null, limit: number) =>
    [...notificationKeys.lists(), { filter, projectId, limit }] as const,
  unreadCounts: () => [...notificationKeys.all, "unread-count"] as const,
  unreadCount: (projectId: number | null) =>
    [...notificationKeys.unreadCounts(), projectId] as const,
};
