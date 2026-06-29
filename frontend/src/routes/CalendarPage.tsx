import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import { TaskCalendar } from "../components/TaskCalendar";
import { useBoardQuery } from "../features/issues/hooks/useBoardQuery";

export function CalendarPage() {
  const { projectKey } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const page = Number(searchParams.get("page") ?? "1");
  const calendarQuery = useBoardQuery(projectKey, page);

  return (
    <div className="flex flex-col gap-4">
      <div>
        <div className="text-xs font-medium uppercase tracking-wide text-neutral-500">Calendar view</div>
        <h2 className="mt-1 text-xl font-semibold text-neutral-900">Due dates</h2>
      </div>
      <TaskCalendar
        tasks={calendarQuery.data?.items ?? []}
        onTaskClick={(task) => navigate(`/issues/${task.key}`)}
      />
    </div>
  );
}
