import { useQuery } from "@tanstack/react-query";

import { taskApi } from "../../../api/tasks";
import { useProjectByKeyQuery } from "../../projects/hooks/useProjectByKeyQuery";

export function useBoardQuery(projectKey?: string, page = 1) {
  const projectQuery = useProjectByKeyQuery(projectKey);

  const boardQuery = useQuery({
    queryKey: ["board", projectKey, page],
    queryFn: () =>
      taskApi.getAll({
        project_id: projectQuery.data!.id,
        page,
        size: 20,
      }),
    enabled: !!projectQuery.data,
  });

  return {
    projectQuery,
    ...boardQuery,
  };
}
