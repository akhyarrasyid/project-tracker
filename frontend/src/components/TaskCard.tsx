import { useState } from "react";
import type { Task, TaskStatus, TaskUpdate } from "../types/task";

// ── Priority colour map ──────────────────────────────────────────────────────

const PRIORITY_COLORS: Record<string, string> = {
  Critical: "bg-red-100 text-red-700 border-red-200",
  High: "bg-orange-100 text-orange-700 border-orange-200",
  Medium: "bg-yellow-50 text-yellow-700 border-yellow-200",
  Low: "bg-slate-100 text-slate-600 border-slate-200",
};

const STATUS_NEXT: Record<TaskStatus, TaskStatus | null> = {
  Todo: "In Progress",
  "In Progress": "Review",
  Review: "Done",
  Blocked: "In Progress",
  Done: null,
};

interface Props {
  task: Task;
  onUpdate: (id: number, data: TaskUpdate) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
}

export function TaskCard({ task, onUpdate, onDelete }: Props) {
  const [loading, setLoading] = useState(false);

  const handleStatusAdvance = async () => {
    const next = STATUS_NEXT[task.status];
    if (!next) return;
    setLoading(true);
    await onUpdate(task.id, { status: next });
    setLoading(false);
  };

  const handleDelete = async () => {
    if (!confirm(`Hapus task "${task.title}"?`)) return;
    setLoading(true);
    try {
      await onDelete(task.id);
    } catch {
      setLoading(false);
    }
  };

  const nextStatus = STATUS_NEXT[task.status];
  const dueDate = new Date(task.due_date).toLocaleDateString("id-ID", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
  const isOverdue =
    task.status !== "Done" && new Date(task.due_date) < new Date();

  return (
    <div
      className={`group relative bg-white rounded-xl border-2 p-4 shadow-sm hover:shadow-md transition-all duration-200 ${
        loading ? "opacity-60 pointer-events-none" : ""
      }`}
    >
      {/* Header row: priority badge + delete */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <span
          className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${
            PRIORITY_COLORS[task.priority] || PRIORITY_COLORS.Low
          }`}
        >
          {task.priority}
        </span>
        <button
          onClick={handleDelete}
          title="Hapus"
          className="opacity-0 group-hover:opacity-100 p-1 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 transition-all"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
            />
          </svg>
        </button>
      </div>

      {/* Title */}
      <h3
        className={`font-semibold text-slate-800 text-sm leading-snug mb-1 ${
          task.status === "Done" ? "line-through text-slate-400" : ""
        }`}
      >
        {task.title}
      </h3>

      {/* Description */}
      {task.description && (
        <p className="text-xs text-slate-500 leading-relaxed line-clamp-2 mb-2">
          {task.description}
        </p>
      )}

      {/* Meta row: assignee + due date */}
      <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
        <span className="truncate max-w-[60%]" title={task.assignee}>
          👤 {task.assignee}
        </span>
        <span
          className={`shrink-0 ${isOverdue ? "text-red-500 font-medium" : ""}`}
          title="Due date"
        >
          📅 {dueDate}
        </span>
      </div>

      {/* Progress bar */}
      {task.progress_percentage > 0 && (
        <div className="mb-2">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-0.5">
            <span>Progress</span>
            <span>{task.progress_percentage}%</span>
          </div>
          <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-400 rounded-full transition-all"
              style={{ width: `${task.progress_percentage}%` }}
            />
          </div>
        </div>
      )}

      {/* Tags */}
      {task.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {task.tags.map((tag) => (
            <span
              key={tag}
              className="text-xs bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded"
            >
              #{tag}
            </span>
          ))}
        </div>
      )}

      {/* Footer row: SP + advance button */}
      <div className="flex items-center justify-between text-xs text-slate-400 mt-1">
        <span title="Story points">⚡ {task.story_points} SP</span>
        {nextStatus && (
          <button
            onClick={handleStatusAdvance}
            className="text-blue-400 hover:text-blue-600 hover:underline transition-colors font-medium"
            title={`Pindah ke ${nextStatus}`}
          >
            → {nextStatus}
          </button>
        )}
      </div>
    </div>
  );
}
