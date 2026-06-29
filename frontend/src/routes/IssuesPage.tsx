import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import { TaskTaskList } from "../components/TaskTaskList";
import { useBoardQuery } from "../features/issues/hooks/useBoardQuery";

export function IssuesPage() {
  const { projectKey } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const page = Number(searchParams.get("page") ?? "1");
  const issuesQuery = useBoardQuery(projectKey, page);

  return (
    <div className="flex flex-col gap-4">
      <div>
        <div className="text-xs font-medium uppercase tracking-wide text-neutral-500">Issues view</div>
        <h2 className="mt-1 text-xl font-semibold text-neutral-900">Project issues</h2>
      </div>
      <TaskTaskList
        tasks={issuesQuery.data?.items ?? []}
        onTaskClick={(task) => navigate(`/issues/${task.key}`)}
      />
    </div>
  );
}
