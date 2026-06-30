import { useQuery } from "@tanstack/react-query";

import { projectApi } from "../../../api/projects";

export function useProjectSummaryQuery(projectId?: number) {
  return useQuery({
    queryKey: ["project-summary", projectId],
    queryFn: () => projectApi.getSummary(projectId!),
    enabled: typeof projectId === "number",
  });
}
