import client from "./client";
import type {
  NotificationBulkMarkReadResponse,
  NotificationFilter,
  NotificationListResponse,
  NotificationMutationResponse,
  NotificationUnreadCountResponse,
} from "../types/notification";

interface ListNotificationsParams {
  filter: NotificationFilter;
  cursor?: string | null;
  limit?: number;
  projectId?: number | null;
}

function buildSearchParams(params: ListNotificationsParams) {
  const searchParams = new URLSearchParams();
  searchParams.set("filter", params.filter);
  if (params.cursor) {
    searchParams.set("cursor", params.cursor);
  }
  if (typeof params.limit === "number") {
    searchParams.set("limit", String(params.limit));
  }
  if (typeof params.projectId === "number") {
    searchParams.set("project_id", String(params.projectId));
  }
  return searchParams.toString();
}

export const notificationApi = {
  list: ({ filter, cursor, limit = 25, projectId }: ListNotificationsParams) =>
    client
      .get<NotificationListResponse>(
        `/api/v1/notifications?${buildSearchParams({ filter, cursor, limit, projectId })}`,
      )
      .then((response) => response.data),

  getUnreadCount: (projectId?: number | null) => {
    const suffix =
      typeof projectId === "number" ? `?project_id=${encodeURIComponent(String(projectId))}` : "";
    return client
      .get<NotificationUnreadCountResponse>(`/api/v1/notifications/unread-count${suffix}`)
      .then((response) => response.data);
  },

  markRead: (notificationId: number) =>
    client
      .patch<NotificationMutationResponse>(`/api/v1/notifications/${notificationId}/read`)
      .then((response) => response.data),

  markUnread: (notificationId: number) =>
    client
      .patch<NotificationMutationResponse>(`/api/v1/notifications/${notificationId}/unread`)
      .then((response) => response.data),

  markAllRead: () =>
    client
      .post<NotificationBulkMarkReadResponse>("/api/v1/notifications/mark-all-read")
      .then((response) => response.data),
};
