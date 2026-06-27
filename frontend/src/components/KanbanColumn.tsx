import { useState } from "react";
import type { Task, TaskStatus } from "../types/task";
import { TaskCard } from "./TaskCard";

const COLUMN_STYLES: Record<
  string,
  { header: string; dot: string; count: string; bg: string }
> = {
  Todo: {
    header: "text-slate-600",
    dot: "bg-slate-400",
    count: "bg-slate-100 text-slate-500",
    bg: "bg-slate-50/50",
  },
  "In Progress": {
    header: "text-blue-600",
    dot: "bg-blue-500",
    count: "bg-blue-50 text-blue-600",
    bg: "bg-blue-50/10",
  },
  Review: {
    header: "text-purple-600",
    dot: "bg-purple-500",
    count: "bg-purple-50 text-purple-600",
    bg: "bg-purple-50/10",
  },
  Done: {
    header: "text-emerald-600",
    dot: "bg-emerald-500",
    count: "bg-emerald-50 text-emerald-600",
    bg: "bg-emerald-50/10",
  },
};

interface Props {
  status: string; // "Todo" | "In Progress" | "Review" | "Done"
  tasks: Task[];
  onUpdate: (id: number, data: any) => Promise<any>;
  onDelete: (id: number) => Promise<void>;
  onTaskClick: (task: Task) => void;
  extra?: React.ReactNode;
}

export function KanbanColumn({ status, tasks, onUpdate, onDelete, onTaskClick, extra }: Props) {
  const [isDragOver, setIsDragOver] = useState(false);
  const style = COLUMN_STYLES[status] || COLUMN_STYLES.Todo;

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const taskIdStr = e.dataTransfer.getData("text/plain");
    if (!taskIdStr) return;
    const taskId = Number(taskIdStr);
    
    // Determine the status to save to backend
    // Since our columns are: Todo, In Progress, Review, Done
    // We update to the exact column name
    const newStatus = status === "Review" ? "Review" : (status as TaskStatus);
    await onUpdate(taskId, { status: newStatus });
  };

  const displayName = status === "Review" ? "In Review" : status;

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`flex flex-col gap-3 min-h-[450px] p-3 rounded-xl border transition-all duration-200 ${
        isDragOver ? "border-blue-400 bg-blue-50/20 shadow-md scale-[1.01]" : "border-slate-100 " + style.bg
      }`}
    >
      {/* Column header */}
      <div className="flex items-center gap-2 px-1">
        <span className={`w-2.5 h-2.5 rounded-full ${style.dot}`} />
        <h2 className={`text-sm font-bold uppercase tracking-wider ${style.header}`}>
          {displayName}
        </h2>
        <span className={`ml-auto text-xs font-semibold px-2 py-0.5 rounded-full ${style.count}`}>
          {tasks.length}
        </span>
      </div>

      {/* Task list container */}
      <div className="flex-1 flex flex-col gap-2 overflow-y-auto min-h-[100px]">
        {tasks.map((task) => (
          <TaskCard
            key={task.id}
            task={task}
            onUpdate={onUpdate}
            onDelete={onDelete}
            onTaskClick={onTaskClick}
          />
        ))}

        {tasks.length === 0 && !extra && (
          <div className="text-center py-12 text-slate-300 text-sm border-2 border-dashed border-slate-200/50 rounded-xl bg-white/50">
            Tidak ada task
          </div>
        )}
      </div>

      {/* Extra slot (e.g. create button/form) */}
      {extra}
    </div>
  );
}
