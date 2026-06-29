import { useMemo } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import { TaskTaskList } from "../components/TaskTaskList";
import { IssueDetailPanel } from "../features/issues/components/IssueDetailPanel";
import { useBoardQuery } from "../features/issues/hooks/useBoardQuery";

export function IssuesPage() {
  const { projectKey } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const issuesQuery = useBoardQuery(projectKey);
  const tasks = useMemo(
    () =>
      Object.values(issuesQuery.data?.columns ?? {}).flatMap((column) => column.items),
    [issuesQuery.data],
  );

  return (
    <div className="flex flex-col gap-4">
      <div>
        <div className="text-xs font-medium uppercase tracking-wide text-neutral-500">Issues view</div>
        <h2 className="mt-1 text-xl font-semibold text-neutral-900">Project issues</h2>
      </div>
      <TaskTaskList
        tasks={tasks}
        onTaskClick={(task) => {
          const nextParams = new URLSearchParams(searchParams);
          nextParams.set("issue", task.key);
          setSearchParams(nextParams);
        }}
      />
      <IssueDetailPanel
        issueKey={searchParams.get("issue") ?? undefined}
        mode="sheet"
        onClose={() => {
          const nextParams = new URLSearchParams(searchParams);
          nextParams.delete("issue");
          setSearchParams(nextParams);
        }}
      />
    </div>
  );
}
