import type { TaskPriority, TaskStatus } from "../types/task";

export const STATUS_META: Record<
  TaskStatus,
  { label: string; dotClassName: string; badgeClassName: string; railClassName: string }
> = {
  Todo: {
    label: "To do",
    dotClassName: "bg-slate-400",
    badgeClassName:
      "border border-slate-500/20 bg-slate-500/12 text-slate-600",
    railClassName: "bg-slate-400",
  },
  "In Progress": {
    label: "In progress",
    dotClassName: "bg-sky-500",
    badgeClassName:
      "border border-sky-500/25 bg-sky-500/14 text-sky-600",
    railClassName: "bg-sky-500",
  },
  Review: {
    label: "In review",
    dotClassName: "bg-violet-500",
    badgeClassName:
      "border border-violet-500/25 bg-violet-500/14 text-violet-600",
    railClassName: "bg-violet-500",
  },
  Done: {
    label: "Done",
    dotClassName: "bg-emerald-500",
    badgeClassName:
      "border border-emerald-500/25 bg-emerald-500/14 text-emerald-600",
    railClassName: "bg-emerald-500",
  },
};

export const PRIORITY_META: Record<
  TaskPriority,
  { label: string; chipClassName: string }
> = {
  Low: {
    label: "Low",
    chipClassName: "border border-slate-500/20 bg-slate-500/12 text-slate-600",
  },
  Medium: {
    label: "Medium",
    chipClassName:
      "border border-amber-500/25 bg-amber-500/16 text-amber-600",
  },
  High: {
    label: "High",
    chipClassName:
      "border border-orange-500/25 bg-orange-500/16 text-orange-600",
  },
  Critical: {
    label: "Critical",
    chipClassName: "border border-rose-500/25 bg-rose-500/16 text-rose-600",
  },
};

export function formatStatusLabel(status: TaskStatus) {
  return STATUS_META[status].label;
}
