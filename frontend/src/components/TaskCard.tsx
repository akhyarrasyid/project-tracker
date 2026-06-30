import { AlertCircle, CalendarDays, MessageSquareText, Tag, UserCircle2 } from "lucide-react";

import { PRIORITY_META, STATUS_META } from "../app/issue-appearance";
import type { Task } from "../types/task";

interface Props {
  readonly task: Task;
  readonly onTaskClick: (task: Task) => void;
}

export function TaskCard({ task, onTaskClick }: Props) {
  const dueDate = new Date(task.due_date).toLocaleDateString("id-ID", {
    day: "numeric",
    month: "short",
  });
  const statusMeta = STATUS_META[task.status];
  const priorityMeta = PRIORITY_META[task.priority];

  return (
    <div className="app-card group relative overflow-hidden rounded-2xl">
      <div className={`absolute inset-y-0 left-0 w-1 ${statusMeta.railClassName}`} />

      <button type="button" onClick={() => onTaskClick(task)} className="block w-full px-4 py-3.5 text-left">
        <div className="mb-3 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[11px] font-semibold tracking-[0.08em] text-[color:var(--app-text-soft)]">
                {task.key}
              </span>
              <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${priorityMeta.chipClassName}`}>
                {priorityMeta.label}
              </span>
              {task.is_blocked ? (
                <span className="inline-flex items-center gap-1 rounded-full border border-rose-500/20 bg-rose-500/10 px-2 py-0.5 text-[11px] font-medium text-rose-600">
                  <AlertCircle className="h-3.5 w-3.5" />
                  Blocked
                </span>
              ) : null}
            </div>
            <div className="app-heading mt-3 line-clamp-3 text-[15px] font-semibold leading-6">
              {task.title}
            </div>
          </div>

          <span className={`mt-0.5 h-2.5 w-2.5 shrink-0 rounded-full ${statusMeta.dotClassName}`} aria-hidden />
        </div>

        {task.tags.length ? (
          <div className="mb-3 flex flex-wrap gap-1.5">
            {task.tags.slice(0, 2).map((tag) => (
              <span
                key={tag}
                className="inline-flex items-center gap-1 rounded-full border border-[color:var(--app-border)] bg-[color:var(--app-panel-muted)] px-2 py-1 text-[11px] text-[color:var(--app-text-soft)]"
              >
                <Tag className="h-3 w-3" />
                {tag}
              </span>
            ))}
          </div>
        ) : null}

        <div className="flex items-center justify-between gap-3 border-t border-[color:var(--app-border)] pt-3 text-[12px] text-[color:var(--app-text-soft)]">
          <div className="flex min-w-0 items-center gap-1.5">
            <UserCircle2 className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate">{task.assignee || "Unassigned"}</span>
          </div>
          <div className="flex shrink-0 items-center gap-1.5">
            <CalendarDays className="h-3.5 w-3.5" />
            <span>{dueDate}</span>
          </div>
        </div>

        <div className="mt-3 flex items-center justify-between text-[11px] text-[color:var(--app-text-faint)]">
          <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 ${statusMeta.badgeClassName}`}>
            <span className={`h-1.5 w-1.5 rounded-full ${statusMeta.dotClassName}`} />
            {statusMeta.label}
          </span>
          <span className="inline-flex items-center gap-1">
            <MessageSquareText className="h-3.5 w-3.5" />
            {task.comments_count}
          </span>
        </div>
      </button>
    </div>
  );
}
