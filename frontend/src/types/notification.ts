export type NotificationType =
  | "issue_assigned"
  | "issue_mentioned"
  | "issue_commented"
  | "issue_status_changed"
  | "issue_blocked"
  | "issue_unblocked"
  | "watcher_added"
  | "legacy_event";

export type NotificationFilter =
  | "all"
  | "unread"
  | "assigned"
  | "mentions"
  | "watching";

export interface NotificationActor {
  id: number;
  username: string;
  full_name: string;
}

export interface NotificationIssueSummary {
  id: number | null;
  key: string | null;
  title: string | null;
}

export interface NotificationProjectSummary {
  id: number;
  key: string;
  name: string;
}

export interface NotificationItem {
  id: number;
  type: NotificationType;
  title: string;
  body_preview: string | null;
  metadata: Record<string, unknown>;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
  actor: NotificationActor | null;
  issue: NotificationIssueSummary | null;
  project: NotificationProjectSummary | null;
  route_target: string | null;
}

export interface NotificationListResponse {
  items: NotificationItem[];
  next_cursor: string | null;
}

export interface NotificationUnreadCountResponse {
  unread_count: number;
}

export interface NotificationBulkMarkReadResponse {
  updated_count: number;
}

export interface NotificationMutationResponse {
  notification: NotificationItem;
}

export interface WatcherSummary {
  id: number;
  username: string;
  full_name: string;
}

export interface IssueWatchersResponse {
  issue_id: number;
  count: number;
  is_watching: boolean;
  can_manage_watchers: boolean;
  watchers: WatcherSummary[];
}
