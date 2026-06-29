import { useInfiniteQuery } from "@tanstack/react-query";

import { notificationApi } from "../../../api/notifications";
import type { NotificationFilter } from "../../../types/notification";
import { notificationKeys } from "./queryKeys";

interface UseNotificationsQueryOptions {
  filter: NotificationFilter;
  projectId?: number | null;
  limit?: number;
}

export function useNotificationsQuery({
  filter,
  projectId = null,
  limit = 25,
}: UseNotificationsQueryOptions) {
  return useInfiniteQuery({
    queryKey: notificationKeys.list(filter, projectId, limit),
    initialPageParam: null as string | null,
    queryFn: ({ pageParam }) =>
      notificationApi.list({
        filter,
        cursor: pageParam,
        limit,
        projectId,
      }),
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
  });
}
