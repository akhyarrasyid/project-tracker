import { AlertCircle, CalendarDays, UserCircle2 } from "lucide-react";

import type { Task } from "../types/task";

const PRIORITY_STYLES: Record<string, string> = {
  Critical: "text-red-700 bg-red-50",
  High: "text-orange-700 bg-orange-50",
  Medium: "text-amber-700 bg-amber-50",
  Low: "text-neutral-600 bg-neutral-100",
};

interface Props {
  readonly task: Task;
  readonly onTaskClick: (task: Task) => void;
}

export function TaskCard({ task, onTaskClick }: Props) {
  const dueDate = new Date(task.due_date).toLocaleDateString("id-ID", {
    day: "numeric",
    month: "short",
  });

  return (
    <div className="group rounded-lg border border-neutral-200 bg-white p-3 transition hover:border-neutral-300">
      <div className="mb-2 flex items-start gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <span className="text-[11px] font-medium text-neutral-500">{task.key}</span>
          <span
            className={`rounded px-1.5 py-0.5 text-[11px] font-medium ${
              PRIORITY_STYLES[task.priority] ?? PRIORITY_STYLES.Low
            }`}
          >
            {task.priority}
          </span>
          {task.is_blocked && (
            <span className="inline-flex items-center gap-1 text-[11px] text-red-600">
              <AlertCircle className="h-3.5 w-3.5" />
              Blocked
            </span>
          )}
        </div>
      </div>

      <button
        type="button"
        onClick={() => onTaskClick(task)}
        className="w-full text-left"
      >
        <div className="text-sm font-medium leading-5 text-neutral-900">{task.title}</div>
      </button>

      <div className="mt-3 flex items-center justify-between gap-3 text-[12px] text-neutral-500">
        <div className="flex min-w-0 items-center gap-1.5">
          <UserCircle2 className="h-3.5 w-3.5 shrink-0" />
          <span className="truncate">{task.assignee || "Unassigned"}</span>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <CalendarDays className="h-3.5 w-3.5" />
          <span>{dueDate}</span>
        </div>
      </div>
    </div>
  );
}
