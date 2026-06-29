import { useMemo } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import { CreateTaskForm } from "../components/CreateTaskForm";
import { KanbanColumn } from "../components/KanbanColumn";
import { queryClient } from "../app/query-client";
import { taskApi } from "../api/tasks";
import type { Task, TaskCreate, TaskUpdate } from "../types/task";
import { useBoardQuery } from "../features/issues/hooks/useBoardQuery";

const COLUMNS = ["Todo", "In Progress", "Review", "Done"] as const;

export function ProjectBoardPage() {
  const { projectKey } = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Number(searchParams.get("page") ?? "1");
  const boardQuery = useBoardQuery(projectKey, page);

  const groupedTasks = useMemo(() => {
    const tasks = boardQuery.data?.items ?? [];
    return COLUMNS.reduce<Record<string, Task[]>>((accumulator, column) => {
      accumulator[column] = tasks.filter((task) => task.status === column);
      return accumulator;
    }, {});
  }, [boardQuery.data?.items]);

  async function handleCreateTask(payload: TaskCreate, projectId: number) {
    const created = await taskApi.create(payload, projectId);
    await queryClient.invalidateQueries({ queryKey: ["board", projectKey] });
    await queryClient.invalidateQueries({ queryKey: ["my-issues"] });
    return created;
  }

  async function handleUpdateTask(id: number, payload: TaskUpdate) {
    const updated = await taskApi.update(id, payload);
    await queryClient.invalidateQueries({ queryKey: ["board", projectKey] });
    await queryClient.invalidateQueries({ queryKey: ["issue", updated.key] });
    return updated;
  }

  async function handleDeleteTask(id: number) {
    await taskApi.delete(id);
    await queryClient.invalidateQueries({ queryKey: ["board", projectKey] });
    await queryClient.invalidateQueries({ queryKey: ["my-issues"] });
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs font-medium uppercase tracking-wide text-neutral-500">Board view</div>
          <h2 className="mt-1 text-xl font-semibold text-neutral-900">Current work</h2>
        </div>
        <div className="text-sm text-neutral-500">
          {boardQuery.data?.total ?? 0} issues
        </div>
      </div>

      <div className="overflow-x-auto pb-2">
        <div className="grid min-w-[1240px] grid-cols-4 gap-4">
          {COLUMNS.map((column) => (
            <KanbanColumn
              key={column}
              status={column}
              tasks={groupedTasks[column] ?? []}
              onUpdate={handleUpdateTask}
              onDelete={handleDeleteTask}
              onTaskClick={(task) => navigate(`/issues/${task.key}`)}
              extra={
                column === "Todo" ? (
                  <CreateTaskForm
                    onCreate={handleCreateTask}
                    currentProjectId={boardQuery.projectQuery.data?.id}
                  />
                ) : undefined
              }
            />
          ))}
        </div>
      </div>

      <div className="flex items-center justify-end gap-2">
        <button
          type="button"
          onClick={() => setSearchParams({ page: String(Math.max(1, page - 1)) })}
          disabled={page <= 1}
          className="rounded-md border border-neutral-200 px-3 py-2 text-sm text-neutral-700 disabled:opacity-40"
        >
          Previous
        </button>
        <span className="text-sm text-neutral-500">
          {page} / {boardQuery.data?.pages ?? 1}
        </span>
        <button
          type="button"
          onClick={() =>
            setSearchParams({
              page: String(Math.min(boardQuery.data?.pages ?? page, page + 1)),
            })
          }
          disabled={page >= (boardQuery.data?.pages ?? 1)}
          className="rounded-md border border-neutral-200 px-3 py-2 text-sm text-neutral-700 disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  );
}
