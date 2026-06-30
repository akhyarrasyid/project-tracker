import { useDroppable } from "@dnd-kit/core";
import { Plus } from "lucide-react";

import type { Task, TaskStatus } from "../types/task";

interface Props {
  readonly status: TaskStatus;
  readonly tasks: readonly Task[];
  readonly totalCount: number;
  readonly renderTask: (task: Task) => React.ReactNode;
  readonly extra?: React.ReactNode;
}

function formatStatus(status: TaskStatus) {
  return status === "Review" ? "In Review" : status;
}

export function KanbanColumn({ status, tasks, totalCount, renderTask, extra }: Props) {
  const { isOver, setNodeRef } = useDroppable({
    id: `column:${status}`,
    data: { type: "column", status },
  });

  return (
    <section
      ref={setNodeRef}
      className={`flex h-full min-h-[420px] w-[300px] shrink-0 flex-col rounded-lg border bg-neutral-50/60 ${
        isOver ? "border-blue-400" : "border-neutral-200"
      }`}
    >
      <header className="sticky top-0 z-10 flex items-center gap-2 rounded-t-lg border-b border-neutral-200 bg-neutral-50/95 px-4 py-3 backdrop-blur">
        <div className="h-2 w-2 rounded-full bg-neutral-400" />
        <h3 className="text-sm font-medium text-neutral-800">{formatStatus(status)}</h3>
        <span className="rounded bg-neutral-200 px-1.5 py-0.5 text-[11px] text-neutral-600">
          {totalCount}
        </span>
        <Plus className="ml-auto h-4 w-4 text-neutral-400" />
      </header>

      <div className="flex flex-1 flex-col gap-2 p-3">
        {tasks.map((task) => renderTask(task))}
        {tasks.length === 0 && (
          <div className="rounded-lg border border-dashed border-neutral-200 bg-white px-3 py-6 text-center text-sm text-neutral-400">
            No issues
          </div>
        )}
      </div>

      {extra && <div className="border-t border-neutral-200 p-3">{extra}</div>}
    </section>
  );
}
