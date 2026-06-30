import { Bell, CheckCheck, ChevronRight, LoaderCircle, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import {
  useMarkAllNotificationsReadMutation,
  useMarkNotificationReadMutation,
  useMarkNotificationUnreadMutation,
} from "../features/notifications/hooks/useNotificationMutations";
import { useNotificationsQuery } from "../features/notifications/hooks/useNotificationsQuery";
import { useUnreadNotificationCountQuery } from "../features/notifications/hooks/useUnreadNotificationCountQuery";
import type { NotificationFilter, NotificationItem } from "../types/notification";

const FILTERS: Array<{ label: string; value: NotificationFilter }> = [
  { label: "All", value: "all" },
  { label: "Unread", value: "unread" },
  { label: "Assigned", value: "assigned" },
  { label: "Mentions", value: "mentions" },
  { label: "Watching", value: "watching" },
];

function cn(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

function getRelativeTimeLabel(value: string) {
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

function getGroupLabel(value: string) {
  const target = new Date(value);
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfTarget = new Date(
    target.getFullYear(),
    target.getMonth(),
    target.getDate(),
  );
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

function filterNotifications(items: NotificationItem[], search: string) {
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

function groupNotifications(items: NotificationItem[]) {
  const groups = new Map<string, NotificationItem[]>();
  for (const item of items) {
    const key = getGroupLabel(item.created_at);
    const current = groups.get(key) ?? [];
    current.push(item);
    groups.set(key, current);
  }
  return Array.from(groups.entries());
}

export function InboxPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState("");
  const activeFilter = (searchParams.get("filter") as NotificationFilter | null) ?? "all";

  const notificationsQuery = useNotificationsQuery({ filter: activeFilter, limit: 20 });
  const unreadCountQuery = useUnreadNotificationCountQuery();
  const markReadMutation = useMarkNotificationReadMutation();
  const markUnreadMutation = useMarkNotificationUnreadMutation();
  const markAllReadMutation = useMarkAllNotificationsReadMutation();

  const notifications = useMemo(
    () =>
      filterNotifications(
        notificationsQuery.data?.pages.flatMap((page) => page.items) ?? [],
        search,
      ),
    [notificationsQuery.data?.pages, search],
  );

  const groupedNotifications = useMemo(
    () => groupNotifications(notifications),
    [notifications],
  );

  function handleFilterChange(filter: NotificationFilter) {
    const next = new URLSearchParams(searchParams);
    if (filter === "all") {
      next.delete("filter");
    } else {
      next.set("filter", filter);
    }
    setSearchParams(next);
  }

  async function handleOpenNotification(notification: NotificationItem) {
    if (!notification.is_read) {
      await markReadMutation.mutateAsync(notification.id);
    }
    navigate(notification.route_target ?? `/issues/${notification.issue?.key ?? ""}`);
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-[12px] font-medium text-[color:var(--app-text-soft)]">Inbox</div>
          <h1 className="app-heading mt-1 text-3xl font-semibold">Notifications</h1>
          <div className="mt-1 text-sm text-[color:var(--app-text-soft)]">
            {unreadCountQuery.data?.unread_count ?? 0} unread
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <label className="relative min-w-[240px]">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
            <input
              aria-label="Search notifications"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search notifications"
              className="w-full rounded-xl border border-[color:var(--app-border)] bg-[color:var(--app-panel)] py-2.5 pl-9 pr-3 text-sm text-[color:var(--app-heading)] outline-none placeholder:text-[color:var(--app-text-faint)] focus:border-blue-500"
            />
          </label>
          <button
            type="button"
            onClick={() => markAllReadMutation.mutate()}
            disabled={markAllReadMutation.isPending || !unreadCountQuery.data?.unread_count}
            className="inline-flex items-center gap-2 rounded-xl border border-[color:var(--app-border)] bg-[color:var(--app-panel)] px-3 py-2.5 text-sm text-[color:var(--app-text)] disabled:cursor-not-allowed disabled:opacity-50"
          >
            <CheckCheck className="h-4 w-4" />
            Mark all as read
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {FILTERS.map((filter) => (
          <button
            key={filter.value}
            type="button"
            onClick={() => handleFilterChange(filter.value)}
            className={cn(
              "rounded-xl px-3.5 py-2.5 text-sm transition-colors",
              activeFilter === filter.value
                ? "bg-[color:var(--app-heading)] text-white shadow-[0_10px_20px_rgba(15,23,42,0.12)]"
                : "bg-[color:var(--app-panel)] text-[color:var(--app-text-soft)] hover:bg-[color:var(--app-panel-muted)]",
            )}
          >
            {filter.label}
          </button>
        ))}
      </div>

      <div className="app-panel overflow-hidden rounded-[24px]">
        {notificationsQuery.isLoading ? (
          <div className="space-y-3 px-5 py-5">
            {Array.from({ length: 4 }).map((_, index) => (
              <div key={index} className="animate-pulse rounded-2xl border border-[color:var(--app-border)] px-4 py-4">
                <div className="h-3 w-28 rounded bg-[color:var(--app-panel-muted)]" />
                <div className="mt-3 h-4 w-3/4 rounded bg-[color:var(--app-panel-muted)]" />
                <div className="mt-2 h-3 w-2/3 rounded bg-[color:var(--app-panel-muted)]/80" />
              </div>
            ))}
          </div>
        ) : notificationsQuery.isError ? (
          <div className="px-5 py-10 text-sm text-[color:var(--app-text-soft)]">
            <div className="font-medium text-[color:var(--app-heading)]">Couldn&apos;t load notifications.</div>
            <button
              type="button"
              onClick={() => void notificationsQuery.refetch()}
              className="mt-3 rounded-xl border border-[color:var(--app-border)] px-3 py-2 text-sm text-[color:var(--app-text)]"
            >
              Retry
            </button>
          </div>
        ) : !notifications.length ? (
          <div className="px-5 py-12 text-center">
            <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-[color:var(--app-panel-muted)] text-[color:var(--app-text-soft)]">
              <Bell className="h-5 w-5" />
            </div>
            <div className="app-heading mt-4 text-base font-medium">You&apos;re all caught up</div>
            <div className="mt-1 text-sm text-[color:var(--app-text-soft)]">
              {activeFilter === "unread"
                ? "No unread notifications need your attention."
                : "No notifications match this view right now."}
            </div>
          </div>
        ) : (
          <div>
            {groupedNotifications.map(([label, items]) => (
              <section key={label} className="border-b border-[color:var(--app-border)] last:border-b-0">
                <div className="px-5 py-3 text-[12px] font-medium text-[color:var(--app-text-soft)]">{label}</div>
                <div>
                  {items.map((notification) => (
                    <div
                      key={notification.id}
                      className={cn(
                        "grid grid-cols-[auto_minmax(0,1fr)_auto] items-start gap-4 border-t border-[color:var(--app-border)] px-5 py-4",
                        !notification.is_read && "bg-blue-500/[0.05]",
                      )}
                    >
                      <button
                        type="button"
                        onClick={() => void handleOpenNotification(notification)}
                        className="mt-1 flex h-8 w-8 items-center justify-center rounded-full bg-[color:var(--app-panel-muted)] text-[color:var(--app-text-soft)]"
                        aria-label={`Open ${notification.title}`}
                      >
                        <Bell className="h-4 w-4" />
                      </button>

                      <button
                        type="button"
                        onClick={() => void handleOpenNotification(notification)}
                        className="min-w-0 text-left"
                      >
                        <div className="flex items-center gap-2">
                          {!notification.is_read ? (
                            <span className="h-2 w-2 rounded-full bg-blue-600" aria-hidden />
                          ) : null}
                          <div
                            className={cn(
                              "truncate text-sm text-[color:var(--app-heading)]",
                              !notification.is_read && "font-medium",
                            )}
                          >
                            {notification.title}
                          </div>
                        </div>
                        <div className="mt-1 truncate text-sm text-[color:var(--app-text)]">
                          {notification.body_preview || notification.issue?.title || "No preview available."}
                        </div>
                        <div className="mt-2 flex flex-wrap items-center gap-2 text-[12px] text-[color:var(--app-text-soft)]">
                          {notification.project?.name ? <span>{notification.project.name}</span> : null}
                          {notification.issue?.key ? <span>{notification.issue.key}</span> : null}
                          <span>{getRelativeTimeLabel(notification.created_at)}</span>
                        </div>
                      </button>

                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() =>
                            notification.is_read
                              ? markUnreadMutation.mutate(notification.id)
                              : markReadMutation.mutate(notification.id)
                          }
                          className="rounded-xl border border-[color:var(--app-border)] px-2.5 py-2 text-[12px] text-[color:var(--app-text-soft)] hover:bg-[color:var(--app-panel-muted)]"
                        >
                          {notification.is_read ? "Mark unread" : "Mark read"}
                        </button>
                        <button
                          type="button"
                          onClick={() => void handleOpenNotification(notification)}
                          className="rounded-xl border border-[color:var(--app-border)] p-2 text-[color:var(--app-text-soft)] hover:bg-[color:var(--app-panel-muted)]"
                          aria-label={`Open issue ${notification.issue?.key ?? notification.id}`}
                        >
                          <ChevronRight className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            ))}

            {notificationsQuery.hasNextPage ? (
              <div className="flex justify-center border-t border-[color:var(--app-border)] px-5 py-4">
                <button
                  type="button"
                  onClick={() => void notificationsQuery.fetchNextPage()}
                  disabled={notificationsQuery.isFetchingNextPage}
                  className="inline-flex items-center gap-2 rounded-xl border border-[color:var(--app-border)] px-3 py-2 text-sm text-[color:var(--app-text)] disabled:opacity-50"
                >
                  {notificationsQuery.isFetchingNextPage ? (
                    <>
                      <LoaderCircle className="h-4 w-4 animate-spin" />
                      Loading more
                    </>
                  ) : (
                    "Load more"
                  )}
                </button>
              </div>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}
