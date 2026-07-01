import type { IssueActivity, Task } from "../../../types/task";

export function describeActivity(item: IssueActivity) {
  if (item.field && item.old_value && item.new_value) {
    return `${item.actor.full_name} changed ${item.field} from ${item.old_value} to ${item.new_value}`;
  }
  if (item.field && item.new_value) {
    return `${item.actor.full_name} updated ${item.field} to ${item.new_value}`;
  }
  return `${item.actor.full_name} ${item.action.toLowerCase()}`;
}

export function getConflictMessage(error: unknown) {
  const detail = (error as { response?: { data?: { detail?: { message?: string } } } })?.response?.data?.detail;
  return detail?.message ?? null;
}

export function getLatestIssue(error: unknown) {
  const detail = (error as { response?: { data?: { detail?: { latest_issue?: Task } } } })?.response?.data?.detail;
  return detail?.latest_issue ?? null;
}

export function getRequestErrorMessage(error: unknown, fallback: string) {
  const response = (error as { response?: { status?: number; data?: { detail?: unknown } } })?.response;
  const detail = response?.data?.detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (response?.status === 403) {
    return "Akun ini tidak punya izin untuk menghapus issue.";
  }
  if (response?.status === 404) {
    return "Issue ini sudah tidak tersedia atau sudah dihapus.";
  }
  return fallback;
}
