import { useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { TaskCalendar } from "../components/TaskCalendar";
import { useBoardQuery } from "../features/issues/hooks/useBoardQuery";

export function CalendarPage() {
  const { projectKey } = useParams();
  const navigate = useNavigate();
  const calendarQuery = useBoardQuery(projectKey);
  const tasks = useMemo(
    () =>
      Object.values(calendarQuery.data?.columns ?? {}).flatMap((column) => column.items),
    [calendarQuery.data],
  );

  return (
    <div className="flex flex-col gap-4">
      <div>
        <div className="text-xs font-medium uppercase tracking-wide text-neutral-500">Calendar view</div>
        <h2 className="mt-1 text-xl font-semibold text-neutral-900">Due dates</h2>
      </div>
      <TaskCalendar
        tasks={tasks}
        onTaskClick={(task) => navigate(`/issues/${task.key}`)}
      />
    </div>
  );
}
