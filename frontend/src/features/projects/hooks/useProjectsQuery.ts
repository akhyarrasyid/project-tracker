import { useQuery } from "@tanstack/react-query";

import { metaApi } from "../../../api/meta";

export function useProjectsQuery() {
  return useQuery({
    queryKey: ["projects"],
    queryFn: () => metaApi.getProjects(),
  });
}
