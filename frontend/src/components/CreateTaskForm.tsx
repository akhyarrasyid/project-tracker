import { useState } from "react";
import type { TaskCreate, TaskStatus } from "../types/task";

interface Props {
  onCreate: (data: TaskCreate) => Promise<any>;
}

export function CreateTaskForm({ onCreate }: Props) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState<TaskStatus>("Todo");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    if (!title.trim()) {
      setError("Judul tidak boleh kosong.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await onCreate({ title: title.trim(), description: description.trim() || undefined, status });
      setTitle("");
      setDescription("");
      setStatus("Todo");
      setOpen(false);
    } catch {
      setError("Gagal membuat task. Coba lagi.");
    } finally {
      setLoading(false);
    }
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="w-full border-2 border-dashed border-slate-200 rounded-xl py-3 text-sm text-slate-400 hover:border-blue-300 hover:text-blue-400 hover:bg-blue-50 transition-all duration-200 font-medium"
      >
        + Tambah Task Baru
      </button>
    );
  }

  return (
    <div className="bg-white rounded-xl border-2 border-blue-200 p-4 shadow-sm space-y-3">
      <h3 className="text-sm font-semibold text-slate-700">Task Baru</h3>

      <input
        value={title}
        onChange={(e) => { setTitle(e.target.value); setError(""); }}
        placeholder="Judul task..."
        className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
        autoFocus
        onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
      />

      <textarea
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="Deskripsi (opsional)..."
        rows={2}
        className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400 resize-none"
      />

      <select
        value={status}
        onChange={(e) => setStatus(e.target.value as TaskStatus)}
        className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
      >
        <option value="Todo">Todo</option>
        <option value="In Progress">In Progress</option>
        <option value="Done">Done</option>
      </select>

      {error && <p className="text-xs text-red-500">{error}</p>}

      <div className="flex gap-2">
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="flex-1 bg-blue-500 text-white text-sm rounded-lg py-2 hover:bg-blue-600 disabled:opacity-50 transition-colors font-medium"
        >
          {loading ? "Menyimpan..." : "Buat Task"}
        </button>
        <button
          onClick={() => { setOpen(false); setError(""); }}
          className="flex-1 bg-slate-100 text-slate-600 text-sm rounded-lg py-2 hover:bg-slate-200 transition-colors"
        >
          Batal
        </button>
      </div>
    </div>
  );
}
