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
    if (!confirm(`Hapus task "${task.key}: ${task.title}"?`)) return;
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
  });

  const isOverdue = task.status !== "Done" && new Date(task.due_date) < new Date();

  return (
    <div
      draggable
      onDragStart={handleDragStart}
      className={`group relative bg-white rounded-xl border border-slate-150 py-2 px-3 shadow-[0_1px_2px_rgba(0,0,0,0.02)] hover:shadow-md cursor-grab active:cursor-grabbing hover:border-blue-300 transition-all duration-150 ${
        loading ? "opacity-60 pointer-events-none" : ""
      }`}
      style={{ minHeight: "72px" }}
    >
      {/* Top row: ID, priority, Blocked status, Delete button */}
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="text-[10px] font-bold text-blue-600 bg-blue-50 px-1 py-0.5 rounded shrink-0">
            {task.key}
          </span>
          <span
            className={`text-[9px] font-bold px-1 py-0.5 rounded border shrink-0 ${
              PRIORITY_COLORS[task.priority] || PRIORITY_COLORS.Low
            }`}
          >
            {task.priority}
          </span>
          {task.is_blocked && (
            <span className="text-[9px] font-bold bg-red-50 text-red-650 px-1 py-0.5 rounded border border-red-100 uppercase tracking-wide shrink-0">
              Blocked
            </span>
          )}
        </div>
        <button
          onClick={handleDelete}
          title="Hapus"
          className="relative z-10 opacity-0 group-hover:opacity-100 p-0.5 rounded text-slate-400 hover:text-red-500 hover:bg-red-50 transition-all cursor-pointer shrink-0"
        >
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
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
      <h3 className="mb-1.5">
        <button
          type="button"
          onClick={() => onTaskClick(task)}
          className={`w-full text-left font-semibold text-slate-800 text-xs leading-snug group-hover:text-blue-600 transition-colors focus:outline-none focus:underline after:absolute after:inset-0 after:rounded-xl line-clamp-1 ${
            task.status === "Done" ? "line-through text-slate-400" : ""
          }`}
        >
          {task.title}
        </button>
      </h3>

      {/* Footer row: Due date, Story Points, Assignee */}
      <div className="flex items-center justify-between text-[10px] text-slate-400 border-t border-slate-50 pt-1.5 mt-auto">
        <span
          className={`shrink-0 flex items-center gap-1 text-[9px] font-medium ${
            isOverdue ? "text-red-500 font-semibold" : ""
          }`}
          title="Due date"
        >
          📅 {dueDate}
        </span>
        <div className="flex items-center gap-1.5">
          <span className="text-[9px] bg-slate-50 text-slate-500 border border-slate-100 px-1 py-0.2 rounded font-bold shrink-0">
            ⚡ {task.story_points}
          </span>
          {task.assignee ? (
            <span
              className="w-4.5 h-4.5 rounded-full bg-blue-105 text-blue-700 flex items-center justify-center font-bold text-[8px] uppercase shrink-0"
              title={task.assignee}
            >
              {task.assignee.substring(0, 2)}
            </span>
          ) : (
            <span
              className="w-4.5 h-4.5 rounded-full bg-slate-100 text-slate-500 flex items-center justify-center font-bold text-[8px] uppercase shrink-0"
              title="Unassigned"
            >
              --
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
