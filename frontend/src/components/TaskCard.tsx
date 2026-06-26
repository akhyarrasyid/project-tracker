import { useState } from "react";
import type { Task, TaskStatus } from "../types/task";

const STATUS_COLORS: Record<TaskStatus, string> = {
  Todo: "bg-slate-100 text-slate-600 border-slate-200",
  "In Progress": "bg-blue-50 text-blue-700 border-blue-200",
  Done: "bg-emerald-50 text-emerald-700 border-emerald-200",
};

const STATUS_NEXT: Record<TaskStatus, TaskStatus> = {
  Todo: "In Progress",
  "In Progress": "Done",
  Done: "Todo",
};

interface Props {
  task: Task;
  onUpdate: (id: number, data: { status?: TaskStatus; title?: string; description?: string }) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
}

export function TaskCard({ task, onUpdate, onDelete }: Props) {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(task.title);
  const [editDesc, setEditDesc] = useState(task.description || "");
  const [loading, setLoading] = useState(false);

  const handleStatusChange = async (status: TaskStatus) => {
    setLoading(true);
    await onUpdate(task.id, { status });
    setLoading(false);
  };

  const handleSaveEdit = async () => {
    if (!editTitle.trim()) return;
    setLoading(true);
    await onUpdate(task.id, { title: editTitle.trim(), description: editDesc.trim() });
    setIsEditing(false);
    setLoading(false);
  };

  const handleDelete = async () => {
    if (!confirm(`Hapus task "${task.title}"?`)) return;
    setLoading(true);
    await onDelete(task.id);
  };

  return (
    <div className={`group relative bg-white rounded-xl border-2 p-4 shadow-sm hover:shadow-md transition-all duration-200 ${loading ? "opacity-60 pointer-events-none" : ""}`}>
      {/* Status badge + actions */}
      <div className="flex items-start justify-between gap-2 mb-3">
        <select
          value={task.status}
          onChange={(e) => handleStatusChange(e.target.value as TaskStatus)}
          className={`text-xs font-semibold px-2 py-1 rounded-full border cursor-pointer focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-blue-400 ${STATUS_COLORS[task.status]}`}
        >
          <option value="Todo">Todo</option>
          <option value="In Progress">In Progress</option>
          <option value="Done">Done</option>
        </select>

        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={() => setIsEditing(!isEditing)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-blue-500 hover:bg-blue-50 transition-colors"
            title="Edit"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
          </button>
          <button
            onClick={handleDelete}
            className="p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors"
            title="Hapus"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>

      {/* Content */}
      {isEditing ? (
        <div className="space-y-2">
          <input
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            className="w-full text-sm font-semibold border border-slate-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-400"
            placeholder="Judul task..."
          />
          <textarea
            value={editDesc}
            onChange={(e) => setEditDesc(e.target.value)}
            rows={2}
            className="w-full text-sm border border-slate-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-400 resize-none"
            placeholder="Deskripsi (opsional)..."
          />
          <div className="flex gap-2">
            <button
              onClick={handleSaveEdit}
              className="flex-1 text-xs bg-blue-500 text-white rounded-lg py-1.5 hover:bg-blue-600 transition-colors font-medium"
            >
              Simpan
            </button>
            <button
              onClick={() => { setIsEditing(false); setEditTitle(task.title); setEditDesc(task.description || ""); }}
              className="flex-1 text-xs bg-slate-100 text-slate-600 rounded-lg py-1.5 hover:bg-slate-200 transition-colors"
            >
              Batal
            </button>
          </div>
        </div>
      ) : (
        <>
          <h3 className={`font-semibold text-slate-800 text-sm leading-snug mb-1 ${task.status === "Done" ? "line-through text-slate-400" : ""}`}>
            {task.title}
          </h3>
          {task.description && (
            <p className="text-xs text-slate-500 leading-relaxed line-clamp-2">{task.description}</p>
          )}
          <p className="text-xs text-slate-300 mt-2">
            {new Date(task.created_at).toLocaleDateString("id-ID", { day: "numeric", month: "short" })}
          </p>
        </>
      )}

      {/* Quick advance button */}
      {!isEditing && task.status !== "Done" && (
        <button
          onClick={() => handleStatusChange(STATUS_NEXT[task.status])}
          className="mt-3 w-full text-xs text-slate-400 hover:text-blue-500 border border-dashed border-slate-200 hover:border-blue-300 rounded-lg py-1.5 transition-all hover:bg-blue-50"
        >
          → Pindah ke {STATUS_NEXT[task.status]}
        </button>
      )}
    </div>
  );
}
