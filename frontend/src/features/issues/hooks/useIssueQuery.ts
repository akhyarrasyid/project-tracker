import { useQuery } from "@tanstack/react-query";

import { issueApi } from "../../../api/issues";

export function useIssueQuery(issueKey?: string) {
  return useQuery({
    queryKey: ["issue", issueKey],
    queryFn: () => issueApi.getByKey(issueKey!),
    enabled: Boolean(issueKey),
  });
}
