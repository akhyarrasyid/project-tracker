import { useQuery } from "@tanstack/react-query";

import { taskApi } from "../../../api/tasks";

export function useMyIssuesQuery(userId?: number) {
  return useQuery({
    queryKey: ["my-issues", userId],
    queryFn: () =>
      taskApi.getAll({
        assignee_id: userId,
        page: 1,
        size: 20,
        sort_by: "due_date",
        sort_order: "asc",
      }),
    enabled: typeof userId === "number",
  });
}
