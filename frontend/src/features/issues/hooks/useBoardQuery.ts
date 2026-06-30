import { useQuery } from "@tanstack/react-query";

import { projectApi } from "../../../api/projects";
import { useProjectByKeyQuery } from "../../projects/hooks/useProjectByKeyQuery";

export function useBoardQuery(projectKey?: string) {
  const projectQuery = useProjectByKeyQuery(projectKey);

  const boardQuery = useQuery({
    queryKey: ["board", projectKey],
    queryFn: () => projectApi.getBoard(projectQuery.data!.id, { limit: 50, start: true }),
    enabled: !!projectQuery.data,
  });

  return {
    projectQuery,
    ...boardQuery,
  };
}
