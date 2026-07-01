import type { NotificationItem } from "../types/notification";
import type { BoardResponse, IssueMoveInput, TaskStatus } from "../types/task";

const COLUMNS: TaskStatus[] = ["Todo", "In Progress", "Review", "Done"];

export function findTask(board: BoardResponse, taskId: number) {
  for (const status of COLUMNS) {
    const task = board.columns[status].items.find((item) => item.id === taskId);
    if (task) {
      return task;
    }
  }
  return null;
}

export function buildMoveInput(
  board: BoardResponse,
  activeTaskId: number,
  overId: string,
): IssueMoveInput | null {
  if (overId.startsWith("column:")) {
    const status = overId.replace("column:", "") as TaskStatus;
    const items = board.columns[status].items.filter((item) => item.id !== activeTaskId);
    const last = items.at(-1);
    return {
      status,
      after_issue_id: last?.id ?? null,
    };
  }

  if (!overId.startsWith("task:")) {
    return null;
  }

  const overTaskId = Number(overId.replace("task:", ""));
  const overTask = findTask(board, overTaskId);
  if (!overTask) {
    return null;
  }

  const status = overTask.status;
  const items = board.columns[status].items.filter((item) => item.id !== activeTaskId);
  const overIndex = items.findIndex((item) => item.id === overTaskId);
  const previous = overIndex > 0 ? items[overIndex - 1] : null;

  return {
    status,
    before_issue_id: overTask.id,
    after_issue_id: previous?.id ?? null,
  };
}

export function getRelativeTimeLabel(value: string) {
  const target = new Date(value).getTime();
  const diffMinutes = Math.round((target - Date.now()) / 60_000);
  const formatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

  if (Math.abs(diffMinutes) < 60) {
    return formatter.format(diffMinutes, "minute");
  }

  const diffHours = Math.round(diffMinutes / 60);
  if (Math.abs(diffHours) < 24) {
    return formatter.format(diffHours, "hour");
  }

  const diffDays = Math.round(diffHours / 24);
  return formatter.format(diffDays, "day");
}

export function getGroupLabel(value: string) {
  const target = new Date(value);
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfTarget = new Date(target.getFullYear(), target.getMonth(), target.getDate());
  const diffDays = Math.round(
    (startOfToday.getTime() - startOfTarget.getTime()) / 86_400_000,
  );

  if (diffDays <= 0) {
    return "Today";
  }
  if (diffDays === 1) {
    return "Yesterday";
  }
  return "Earlier";
}

export function filterNotifications(items: NotificationItem[], search: string) {
  const needle = search.trim().toLowerCase();
  if (!needle) {
    return items;
  }

  return items.filter((item) => {
    const haystacks = [
      item.title,
      item.body_preview ?? "",
      item.issue?.key ?? "",
      item.issue?.title ?? "",
      item.project?.name ?? "",
      item.actor?.full_name ?? "",
    ];
    return haystacks.some((value) => value.toLowerCase().includes(needle));
  });
}

export function groupNotifications(items: NotificationItem[]) {
  const groups = new Map<string, NotificationItem[]>();
  for (const item of items) {
    const key = getGroupLabel(item.created_at);
    const current = groups.get(key) ?? [];
    current.push(item);
    groups.set(key, current);
  }
  return Array.from(groups.entries());
}
