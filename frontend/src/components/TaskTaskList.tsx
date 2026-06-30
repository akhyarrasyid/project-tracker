import { CalendarDays, ChevronDown, ChevronUp, ChevronsUpDown, UserCircle2 } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { PRIORITY_META, STATUS_META, formatStatusLabel } from "../app/issue-appearance";
import type { Task } from "../types/task";

interface Props {
  readonly tasks: readonly Task[];
  readonly onTaskClick: (task: Task) => void;
}

type SortField =
  | "id"
  | "title"
  | "assignee"
  | "created_by"
  | "priority"
  | "status"
  | "story_points"
  | "due_date";
type SortOrder = "asc" | "desc" | null;

const PRIORITY_ORDER: Record<string, number> = {
  Critical: 4,
  High: 3,
  Medium: 2,
  Low: 1,
};

const STATUS_ORDER: Record<string, number> = {
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
    if (!sortField || !sortOrder) {
      return tasks;
    }

    return [...tasks].sort((a, b) => {
      let valA: string | number | null | undefined = a[sortField as keyof Task] as never;
      let valB: string | number | null | undefined = b[sortField as keyof Task] as never;

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

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (sortedTasks.length === 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev < sortedTasks.length - 1 ? prev + 1 : prev));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev > 0 ? prev - 1 : 0));
    } else if (e.key === "Enter" && selectedIndex >= 0 && selectedIndex < sortedTasks.length) {
      e.preventDefault();
      onTaskClick(sortedTasks[selectedIndex]);
    }
  };

  useEffect(() => {
    if (selectedIndex >= 0 && containerRef.current) {
      const selectedRow = containerRef.current.querySelector(`[data-index="${selectedIndex}"]`);
      selectedRow?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }, [selectedIndex]);

  if (tasks.length === 0) {
    return (
      <div className="app-panel rounded-[24px] p-16 text-center text-[color:var(--app-text-soft)]">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-[color:var(--app-panel-muted)]">
          <CalendarDays className="h-5 w-5" />
        </div>
        <span className="text-sm font-medium">Tidak ada issue yang cocok dengan filter aktif</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <div
        ref={containerRef}
        onKeyDown={handleKeyDown}
        tabIndex={0}
        className="app-panel app-scrollbar max-h-[680px] overflow-auto rounded-[24px] focus:outline-none"
      >
        <table className="w-full border-collapse text-left">
          <thead>
            <tr className="sticky top-0 z-10 border-b border-[color:var(--app-border)] bg-[color:var(--app-panel)]">
              <HeaderCell label="ID" field="id" sortField={sortField} sortOrder={sortOrder} onSort={handleSort} />
              <HeaderCell
                label="Summary / title"
                field="title"
                sortField={sortField}
                sortOrder={sortOrder}
                onSort={handleSort}
              />
              <HeaderCell
                label="Assignee"
                field="assignee"
                sortField={sortField}
                sortOrder={sortOrder}
                onSort={handleSort}
              />
              <HeaderCell
                label="Reporter"
                field="created_by"
                sortField={sortField}
                sortOrder={sortOrder}
                onSort={handleSort}
              />
              <HeaderCell
                label="Priority"
                field="priority"
                sortField={sortField}
                sortOrder={sortOrder}
                onSort={handleSort}
              />
              <HeaderCell
                label="Status"
                field="status"
                sortField={sortField}
                sortOrder={sortOrder}
                onSort={handleSort}
              />
              <HeaderCell
                label="SP"
                field="story_points"
                sortField={sortField}
                sortOrder={sortOrder}
                onSort={handleSort}
                centered
              />
              <HeaderCell
                label="Due date"
                field="due_date"
                sortField={sortField}
                sortOrder={sortOrder}
                onSort={handleSort}
              />
            </tr>
          </thead>
          <tbody className="divide-y divide-[color:var(--app-border)] text-sm text-[color:var(--app-text)]">
            {sortedTasks.map((task, index) => {
              const isSelected = selectedIndex === index;
              const priorityMeta = PRIORITY_META[task.priority];
              const statusMeta = STATUS_META[task.status];
              return (
                <tr
                  key={task.id}
                  data-index={index}
                  onClick={() => {
                    setSelectedIndex(index);
                    onTaskClick(task);
                  }}
                  className={`cursor-pointer transition ${
                    isSelected
                      ? "bg-blue-500/[0.08] shadow-[inset_4px_0_0_0_var(--app-accent)]"
                      : "hover:bg-[color:var(--app-panel-muted)]/80"
                  }`}
                >
                  <td className="px-6 py-4 align-top">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedIndex(index);
                        onTaskClick(task);
                      }}
                      className="text-sm font-semibold text-blue-600 hover:underline"
                    >
                      {task.key}
                    </button>
                  </td>
                  <td className="px-6 py-4 align-top">
                    <div className={`max-w-[440px] leading-6 ${isSelected ? "font-semibold" : "font-medium"}`}>
                      {task.title}
                    </div>
                  </td>
                  <td className="px-6 py-4 align-top text-[color:var(--app-text-soft)]">
                    <div className="flex max-w-[170px] items-center gap-2">
                      <UserCircle2 className="h-4 w-4 shrink-0" />
                      <span className="truncate">{task.assignee || "Unassigned"}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 align-top text-[color:var(--app-text-faint)]">{task.created_by}</td>
                  <td className="px-6 py-4 align-top">
                    <span className={`rounded-full px-2.5 py-1 text-[11px] font-medium ${priorityMeta.chipClassName}`}>
                      {priorityMeta.label}
                    </span>
                  </td>
                  <td className="px-6 py-4 align-top">
                    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-medium ${statusMeta.badgeClassName}`}>
                      <span className={`h-1.5 w-1.5 rounded-full ${statusMeta.dotClassName}`} />
                      {formatStatusLabel(task.status)}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-center align-top font-semibold text-[color:var(--app-text-soft)]">
                    {task.story_points}
                  </td>
                  <td className="px-6 py-4 align-top text-[color:var(--app-text-soft)]">
                    <span className="inline-flex items-center gap-2">
                      <CalendarDays className="h-4 w-4" />
                      {new Date(task.due_date).toLocaleDateString("id-ID", {
                        day: "numeric",
                        month: "short",
                      })}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between px-1 text-[11px] text-[color:var(--app-text-faint)]">
        <span>Total: {sortedTasks.length} issues</span>
        <span>Use arrow keys to navigate rows and Enter to open the selected issue.</span>
      </div>
    </div>
  );
}

function HeaderCell({
  label,
  field,
  sortField,
  sortOrder,
  onSort,
  centered = false,
}: {
  label: string;
  field: SortField;
  sortField: SortField | null;
  sortOrder: SortOrder;
  onSort: (field: SortField) => void;
  centered?: boolean;
}) {
  return (
    <th
      onClick={() => onSort(field)}
      className={`px-6 py-3.5 text-[11px] font-semibold tracking-[0.16em] text-[color:var(--app-text-soft)] ${
        centered ? "text-center" : ""
      }`}
    >
      <span className="inline-flex items-center gap-1.5">
        {label}
        {sortField !== field ? (
          <ChevronsUpDown className="h-3.5 w-3.5 opacity-45" />
        ) : sortOrder === "asc" ? (
          <ChevronUp className="h-3.5 w-3.5 text-blue-600" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5 text-blue-600" />
        )}
      </span>
    </th>
  );
}
