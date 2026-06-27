import { useState } from "react";
import type { Task } from "../types/task";

const PRIORITY_COLORS: Record<string, string> = {
  Critical: "bg-red-50 text-red-700 border-red-100",
  High: "bg-orange-50 text-orange-700 border-orange-100",
  Medium: "bg-yellow-50 text-yellow-700 border-yellow-100",
  Low: "bg-slate-50 text-slate-600 border-slate-200",
};

interface Props {
  readonly task: Task;
  readonly onDelete: (id: number) => Promise<void>;
  readonly onTaskClick: (task: Task) => void;
}

export function TaskCard({ task, onDelete, onTaskClick }: Props) {
  const [loading, setLoading] = useState(false);

  const handleDragStart = (e: React.DragEvent) => {
    e.dataTransfer.setData("text/plain", String(task.id));
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation(); // Avoid opening detail modal
    if (!confirm(`Hapus task "WDD-${task.id}: ${task.title}"?`)) return;
    setLoading(true);
    try {
      await onDelete(task.id);
    } catch {
      setLoading(false);
    }
  };

  const dueDate = new Date(task.due_date).toLocaleDateString("id-ID", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });

  const isOverdue = task.status !== "Done" && new Date(task.due_date) < new Date();

  return (
    <div
      draggable
      role="button"
      tabIndex={0}
      onDragStart={handleDragStart}
      onClick={() => onTaskClick(task)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onTaskClick(task);
        }
      }}
      className={`group relative bg-white rounded-xl border border-slate-100 p-4 shadow-sm hover:shadow-md cursor-grab active:cursor-grabbing hover:border-blue-200 transition-all duration-200 ${
        loading ? "opacity-60 pointer-events-none" : ""
      }`}
    >
      {/* Header row: priority badge + ID + delete button */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] font-bold text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded">
            WDD-{task.id}
          </span>
          <span
            className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${
              PRIORITY_COLORS[task.priority] || PRIORITY_COLORS.Low
            }`}
          >
            {task.priority}
          </span>
          {task.status === "Blocked" && (
            <span className="text-[10px] font-bold bg-red-100 text-red-700 px-1.5 py-0.5 rounded border border-red-200 uppercase tracking-wide">
              Blocked
            </span>
          )}
        </div>
        <button
          onClick={handleDelete}
          title="Hapus"
          className="opacity-0 group-hover:opacity-100 p-1 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 transition-all cursor-pointer"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
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
        className={`font-semibold text-slate-800 text-sm leading-snug mb-1 group-hover:text-blue-600 transition-colors ${
          task.status === "Done" ? "line-through text-slate-400" : ""
        }`}
      >
        {task.title}
      </h3>

      {/* Description Summary */}
      {task.description && (
        <p className="text-xs text-slate-400 leading-relaxed line-clamp-2 mb-3">
          {task.description}
        </p>
      )}

      {/* Tags */}
      {task.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {task.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="text-[9px] bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded font-medium"
            >
              #{tag}
            </span>
          ))}
        </div>
      )}

      {/* Progress bar */}
      {task.progress_percentage > 0 && (
        <div className="mb-3">
          <div className="flex items-center justify-between text-[10px] text-slate-400 mb-0.5">
            <span>Progress</span>
            <span>{task.progress_percentage}%</span>
          </div>
          <div className="h-1 bg-slate-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                task.status === "Done" ? "bg-emerald-400" : "bg-blue-400"
              }`}
              style={{ width: `${task.progress_percentage}%` }}
            />
          </div>
        </div>
      )}

      {/* Footer row: SP + assignee avatar */}
      <div className="flex items-center justify-between text-[11px] text-slate-400 border-t border-slate-50 pt-2.5">
        <span
          className={`shrink-0 flex items-center gap-1 ${
            isOverdue ? "text-red-500 font-semibold" : ""
          }`}
          title="Due date"
        >
          📅 {dueDate}
        </span>
        <div className="flex items-center gap-2">
          <span className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded font-bold">
            ⚡ {task.story_points} SP
          </span>
          <span className="w-5 h-5 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-[10px]" title={task.assignee}>
            {task.assignee.substring(0, 2).toUpperCase()}
          </span>
        </div>
      </div>
    </div>
  );
}
