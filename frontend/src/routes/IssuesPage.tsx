import { useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { TaskTaskList } from "../components/TaskTaskList";
import { useBoardQuery } from "../features/issues/hooks/useBoardQuery";

export function IssuesPage() {
  const { projectKey } = useParams();
  const navigate = useNavigate();
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
        onTaskClick={(task) => navigate(`/issues/${task.key}`)}
      />
    </div>
  );
}
