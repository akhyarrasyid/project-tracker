import { useQuery } from "@tanstack/react-query";

import { notificationApi } from "../../../api/notifications";
import { notificationKeys } from "./queryKeys";

export function useUnreadNotificationCountQuery(projectId?: number | null) {
  return useQuery({
    queryKey: notificationKeys.unreadCount(projectId ?? null),
    queryFn: () => notificationApi.getUnreadCount(projectId ?? null),
    staleTime: 15_000,
  });
}
