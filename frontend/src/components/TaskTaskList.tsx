import { useState, useMemo, useEffect, useRef } from "react";
import type { Task } from "../types/task";

interface Props {
  readonly tasks: readonly Task[];
  readonly onTaskClick: (task: Task) => void;
}

type SortField = "id" | "title" | "assignee" | "created_by" | "priority" | "status" | "story_points" | "due_date";
type SortOrder = "asc" | "desc" | null;

const PRIORITY_ORDER: Record<string, number> = {
  Critical: 4,
  High: 3,
  Medium: 2,
  Low: 1,
};

const STATUS_ORDER: Record<string, number> = {
  Blocked: 5,
  Review: 4,
  "In Progress": 3,
  Todo: 2,
  Done: 1,
};

export function TaskTaskList({ tasks, onTaskClick }: Props) {
  const [sortField, setSortField] = useState<SortField | null>(null);
  const [sortOrder, setSortOrder] = useState<SortOrder>(null);
  const [selectedIndex, setSelectedIndex] = useState<number>(-1);
  const containerRef = useRef<HTMLDivElement>(null);

  // Reset selected index when tasks list changes
  useEffect(() => {
    setSelectedIndex(-1);
  }, [tasks]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      if (sortOrder === "asc") {
        setSortOrder("desc");
      } else if (sortOrder === "desc") {
        setSortField(null);
        setSortOrder(null);
      } else {
        setSortOrder("asc");
      }
    } else {
      setSortField(field);
      setSortOrder("asc");
    }
  };

  const sortedTasks = useMemo(() => {
    if (!sortField || !sortOrder) return tasks;

    return [...tasks].sort((a, b) => {
      let valA: any = a[sortField as keyof Task];
      let valB: any = b[sortField as keyof Task];

      if (sortField === "priority") {
        valA = PRIORITY_ORDER[a.priority] || 0;
        valB = PRIORITY_ORDER[b.priority] || 0;
      } else if (sortField === "status") {
        valA = STATUS_ORDER[a.status] || 0;
        valB = STATUS_ORDER[b.status] || 0;
      } else if (sortField === "due_date") {
        valA = new Date(a.due_date).getTime();
        valB = new Date(b.due_date).getTime();
      }

      if (valA === valB) return 0;
      if (valA === null || valA === undefined) return 1;
      if (valB === null || valB === undefined) return -1;

      const comparison = valA < valB ? -1 : 1;
      return sortOrder === "asc" ? comparison : -comparison;
    });
  }, [tasks, sortField, sortOrder]);

  // Handle Keyboard Navigation
  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (sortedTasks.length === 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev < sortedTasks.length - 1 ? prev + 1 : prev));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev > 0 ? prev - 1 : 0));
    } else if (e.key === "Enter") {
      if (selectedIndex >= 0 && selectedIndex < sortedTasks.length) {
        e.preventDefault();
        onTaskClick(sortedTasks[selectedIndex]);
      }
    }
  };

  // Scroll selected row into view if needed
  useEffect(() => {
    if (selectedIndex >= 0 && containerRef.current) {
      const selectedRow = containerRef.current.querySelector(`[data-index="${selectedIndex}"]`);
      if (selectedRow) {
        selectedRow.scrollIntoView({ block: "nearest", behavior: "smooth" });
      }
    }
  }, [selectedIndex]);

  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case "Critical":
        return <span className="bg-red-500/10 text-red-400 border border-red-500/25 px-2.5 py-0.5 rounded-full text-xs font-bold shadow-sm shadow-red-500/5">Critical</span>;
      case "High":
        return <span className="bg-amber-500/10 text-amber-400 border border-amber-500/25 px-2.5 py-0.5 rounded-full text-xs font-bold shadow-sm shadow-amber-500/5">High</span>;
      case "Medium":
        return <span className="bg-blue-500/10 text-blue-400 border border-blue-500/25 px-2.5 py-0.5 rounded-full text-xs font-bold shadow-sm shadow-blue-500/5">Medium</span>;
      default:
        return <span className="bg-slate-500/10 text-slate-400 border border-slate-500/25 px-2.5 py-0.5 rounded-full text-xs font-bold shadow-sm shadow-slate-500/5">Low</span>;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "Todo":
        return <span className="bg-slate-100 text-slate-600 border border-slate-200 px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wide">Todo</span>;
      case "In Progress":
        return <span className="bg-blue-50 text-blue-600 border border-blue-100 px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wide">In Progress</span>;
      case "Review":
        return <span className="bg-purple-50 text-purple-600 border border-purple-100 px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wide">In Review</span>;
      case "Blocked":
        return <span className="bg-red-50 text-red-600 border border-red-100 px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wide">Blocked</span>;
      case "Done":
        return <span className="bg-emerald-50 text-emerald-600 border border-emerald-100 px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wide">Done</span>;
      default:
        return <span className="bg-slate-50 text-slate-500 border border-slate-100 px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wide">{status}</span>;
    }
  };

  const renderSortIcon = (field: SortField) => {
    if (sortField !== field) {
      return (
        <svg className="w-3 h-3 text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity ml-1.5 inline" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
        </svg>
      );
    }
    return sortOrder === "asc" ? (
      <svg className="w-3 h-3 text-blue-600 ml-1.5 inline" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 15l7-7 7 7" />
      </svg>
    ) : (
      <svg className="w-3 h-3 text-blue-600 ml-1.5 inline" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M19 9l-7 7-7-7" />
      </svg>
    );
  };

  if (tasks.length === 0) {
    return (
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-16 text-center text-slate-400">
        <svg className="w-12 h-12 mx-auto mb-4 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
        <span className="text-sm font-medium text-slate-500">Tidak ada task yang cocok dengan filter aktif</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <div
        ref={containerRef}
        onKeyDown={handleKeyDown}
        tabIndex={0}
        className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden focus:outline-none focus:ring-2 focus:ring-blue-500/20 max-h-[600px] overflow-y-auto"
      >
        <table className="w-full text-left border-collapse table-auto">
          <thead>
            <tr className="sticky top-0 bg-slate-50 border-b border-slate-100 z-10 shadow-sm">
              <th
                onClick={() => handleSort("id")}
                className="py-3.5 px-6 text-xs font-extrabold text-slate-500 uppercase tracking-wider cursor-pointer hover:bg-slate-100 hover:text-slate-850 transition-colors group select-none whitespace-nowrap"
              >
                ID {renderSortIcon("id")}
              </th>
              <th
                onClick={() => handleSort("title")}
                className="py-3.5 px-6 text-xs font-extrabold text-slate-500 uppercase tracking-wider cursor-pointer hover:bg-slate-100 hover:text-slate-850 transition-colors group select-none whitespace-nowrap"
              >
                Summary / Title {renderSortIcon("title")}
              </th>
              <th
                onClick={() => handleSort("assignee")}
                className="py-3.5 px-6 text-xs font-extrabold text-slate-500 uppercase tracking-wider cursor-pointer hover:bg-slate-100 hover:text-slate-850 transition-colors group select-none whitespace-nowrap"
              >
                Assignee {renderSortIcon("assignee")}
              </th>
              <th
                onClick={() => handleSort("created_by")}
                className="py-3.5 px-6 text-xs font-extrabold text-slate-500 uppercase tracking-wider cursor-pointer hover:bg-slate-100 hover:text-slate-850 transition-colors group select-none whitespace-nowrap"
              >
                Reporter {renderSortIcon("created_by")}
              </th>
              <th
                onClick={() => handleSort("priority")}
                className="py-3.5 px-6 text-xs font-extrabold text-slate-500 uppercase tracking-wider cursor-pointer hover:bg-slate-100 hover:text-slate-850 transition-colors group select-none whitespace-nowrap"
              >
                Priority {renderSortIcon("priority")}
              </th>
              <th
                onClick={() => handleSort("status")}
                className="py-3.5 px-6 text-xs font-extrabold text-slate-500 uppercase tracking-wider cursor-pointer hover:bg-slate-100 hover:text-slate-850 transition-colors group select-none whitespace-nowrap"
              >
                Status {renderSortIcon("status")}
              </th>
              <th
                onClick={() => handleSort("story_points")}
                className="py-3.5 px-6 text-xs font-extrabold text-slate-500 uppercase tracking-wider cursor-pointer hover:bg-slate-100 hover:text-slate-850 transition-colors group select-none text-center whitespace-nowrap"
              >
                SP {renderSortIcon("story_points")}
              </th>
              <th
                onClick={() => handleSort("due_date")}
                className="py-3.5 px-6 text-xs font-extrabold text-slate-500 uppercase tracking-wider cursor-pointer hover:bg-slate-100 hover:text-slate-850 transition-colors group select-none whitespace-nowrap"
              >
                Due Date {renderSortIcon("due_date")}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-slate-700 text-sm">
            {sortedTasks.map((task, index) => {
              const isSelected = selectedIndex === index;
              return (
                <tr
                  key={task.id}
                  data-index={index}
                  onClick={() => {
                    setSelectedIndex(index);
                    onTaskClick(task);
                  }}
                  className={`cursor-pointer transition-all duration-150 ${
                    isSelected
                      ? "bg-blue-50/50 border-l-4 border-l-blue-600 font-medium"
                      : "hover:bg-slate-50/60"
                  }`}
                >
                  <td className="py-3.5 px-6 font-bold text-blue-600 whitespace-nowrap select-none">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedIndex(index);
                        onTaskClick(task);
                      }}
                      className="font-bold text-blue-600 hover:underline hover:text-blue-700 focus:outline-none"
                    >
                      WDD-{task.id}
                    </button>
                  </td>
                  <td className={`py-3.5 px-6 text-slate-800 ${isSelected ? "font-bold text-blue-900" : ""}`}>
                    {task.title}
                  </td>
                  <td className="py-3.5 px-6 whitespace-nowrap text-slate-600">
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs">👤</span>
                      <span className="truncate max-w-[120px]">{task.assignee || "Unassigned"}</span>
                    </div>
                  </td>
                  <td className="py-3.5 px-6 whitespace-nowrap text-slate-400 text-xs">
                    {task.created_by}
                  </td>
                  <td className="py-3.5 px-6 whitespace-nowrap">
                    {getPriorityBadge(task.priority)}
                  </td>
                  <td className="py-3.5 px-6 whitespace-nowrap">
                    {getStatusBadge(task.status)}
                  </td>
                  <td className="py-3.5 px-6 text-center font-bold text-slate-500">
                    {task.story_points}
                  </td>
                  <td className="py-3.5 px-6 whitespace-nowrap text-slate-500 text-xs">
                    📅 {new Date(task.due_date).toLocaleDateString("id-ID", {
                      day: "numeric",
                      month: "short",
                    })}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between px-3 text-[10px] text-slate-400 font-medium">
        <span>Total: {sortedTasks.length} task</span>
        <span>💡 Tip: Klik tabel & gunakan tombol keyboard ↑ ↓ untuk navigasi, Enter untuk membuka.</span>
      </div>
    </div>
  );
}
