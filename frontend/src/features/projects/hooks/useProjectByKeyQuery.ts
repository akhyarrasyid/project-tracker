import { useMemo } from "react";

import { useProjectsQuery } from "./useProjectsQuery";

export function useProjectByKeyQuery(projectKey?: string) {
  const projectsQuery = useProjectsQuery();

  const project = useMemo(
    () =>
      projectsQuery.data?.find(
        (candidate) => candidate.key.toLowerCase() === projectKey?.toLowerCase(),
      ) ?? null,
    [projectKey, projectsQuery.data],
  );

  return {
    ...projectsQuery,
    data: project,
  };
}
