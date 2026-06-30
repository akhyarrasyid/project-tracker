import { useDroppable } from "@dnd-kit/core";
import { Plus } from "lucide-react";

import { STATUS_META } from "../app/issue-appearance";
import type { Task, TaskStatus } from "../types/task";

interface Props {
  readonly status: TaskStatus;
  readonly tasks: readonly Task[];
  readonly totalCount: number;
  readonly renderTask: (task: Task) => React.ReactNode;
  readonly extra?: React.ReactNode;
}

export function KanbanColumn({ status, tasks, totalCount, renderTask, extra }: Props) {
  const { isOver, setNodeRef } = useDroppable({
    id: `column:${status}`,
    data: { type: "column", status },
  });
  const meta = STATUS_META[status];

  return (
    <section
      ref={setNodeRef}
      className={`app-panel-muted flex h-full min-h-[460px] w-[320px] shrink-0 flex-col rounded-3xl ${
        isOver ? "border-blue-500 shadow-[0_0_0_3px_rgba(37,99,235,0.12)]" : ""
      }`}
    >
      <header className="sticky top-0 z-10 flex items-center gap-2 rounded-t-3xl border-b border-[color:var(--app-border)] bg-[color:var(--app-panel)] px-4 py-3 backdrop-blur">
        <div className={`h-2.5 w-2.5 rounded-full ${meta.dotClassName}`} />
        <h3 className="app-heading text-sm font-semibold">{meta.label}</h3>
        <span className="rounded-full bg-[color:var(--app-panel-muted)] px-2 py-0.5 text-[11px] font-medium text-[color:var(--app-text-soft)]">
          {totalCount}
        </span>
        <button
          type="button"
          className="ml-auto rounded-full p-1 text-[color:var(--app-text-faint)] transition hover:bg-[color:var(--app-panel-muted)] hover:text-[color:var(--app-heading)]"
          aria-label={`Add issue to ${meta.label}`}
        >
          <Plus className="h-4 w-4" />
        </button>
      </header>

      <div className="app-scrollbar flex flex-1 flex-col gap-3 overflow-y-auto p-3">
        {tasks.map((task) => renderTask(task))}
        {tasks.length === 0 && (
          <div className="rounded-2xl border border-dashed border-[color:var(--app-border)] bg-[color:var(--app-panel)] px-3 py-8 text-center text-sm text-[color:var(--app-text-faint)]">
            No issues in {meta.label.toLowerCase()}
          </div>
        )}
      </div>

      {extra ? <div className="border-t border-[color:var(--app-border)] p-3">{extra}</div> : null}
    </section>
  );
}
