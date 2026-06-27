import type { Task, TaskStatus, TaskUpdate } from "../types/task";
import { TaskCard } from "./TaskCard";

// ── Column style map — all 5 statuses ────────────────────────────────────────

const COLUMN_STYLES: Record<
  TaskStatus,
  { header: string; dot: string; count: string }
> = {
  Todo: {
    header: "text-slate-600",
    dot: "bg-slate-400",
    count: "bg-slate-100 text-slate-500",
  },
  "In Progress": {
    header: "text-blue-600",
    dot: "bg-blue-500",
    count: "bg-blue-50 text-blue-600",
  },
  Review: {
    header: "text-purple-600",
    dot: "bg-purple-500",
    count: "bg-purple-50 text-purple-600",
  },
  Blocked: {
    header: "text-red-600",
    dot: "bg-red-500",
    count: "bg-red-50 text-red-600",
  },
  Done: {
    header: "text-emerald-600",
    dot: "bg-emerald-500",
    count: "bg-emerald-50 text-emerald-600",
  },
};

interface Props {
  status: TaskStatus;
  tasks: Task[];
  onUpdate: (id: number, data: TaskUpdate) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
  extra?: React.ReactNode;
}

export function KanbanColumn({ status, tasks, onUpdate, onDelete, extra }: Props) {
  const style = COLUMN_STYLES[status];

  return (
    <div className="flex flex-col gap-3 min-h-[200px]">
      {/* Column header */}
      <div className="flex items-center gap-2 px-1">
        <span className={`w-2 h-2 rounded-full ${style.dot}`} />
        <h2 className={`text-sm font-bold uppercase tracking-wider ${style.header}`}>
          {status}
        </h2>
        <span
          className={`ml-auto text-xs font-semibold px-2 py-0.5 rounded-full ${style.count}`}
        >
          {tasks.length}
        </span>
      </div>

      {/* Task cards */}
      {tasks.map((task) => (
        <TaskCard key={task.id} task={task} onUpdate={onUpdate} onDelete={onDelete} />
      ))}

      {/* Empty state */}
      {tasks.length === 0 && !extra && (
        <div className="text-center py-8 text-slate-300 text-sm border-2 border-dashed border-slate-100 rounded-xl">
          Tidak ada task
        </div>
      )}

      {/* Extra slot (e.g. create form) */}
      {extra}
    </div>
  );
}
