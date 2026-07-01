import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { InboxPage } from "./InboxPage";

const {
  navigate,
  setSearchParams,
  notificationsQuery,
  unreadCountQuery,
  markReadMutation,
  markUnreadMutation,
  markAllReadMutation,
  searchParamsState,
} = vi.hoisted(() => ({
  navigate: vi.fn(),
  setSearchParams: vi.fn(),
  notificationsQuery: vi.fn(),
  unreadCountQuery: vi.fn(),
  markReadMutation: vi.fn(),
  markUnreadMutation: vi.fn(),
  markAllReadMutation: vi.fn(),
  searchParamsState: {
    value: new URLSearchParams(),
  },
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => navigate,
    useSearchParams: () => [searchParamsState.value, setSearchParams],
  };
});

vi.mock("../features/notifications/hooks/useNotificationsQuery", () => ({
  useNotificationsQuery: notificationsQuery,
}));

vi.mock("../features/notifications/hooks/useUnreadNotificationCountQuery", () => ({
  useUnreadNotificationCountQuery: unreadCountQuery,
}));

vi.mock("../features/notifications/hooks/useNotificationMutations", () => ({
  useMarkNotificationReadMutation: markReadMutation,
  useMarkNotificationUnreadMutation: markUnreadMutation,
  useMarkAllNotificationsReadMutation: markAllReadMutation,
}));

const baseNotification = {
  id: 11,
  type: "issue_assigned",
  title: "Demo Admin assigned you to PAY-86",
  body_preview: "Handle duplicate payment callback",
  is_read: false,
  created_at: new Date().toISOString(),
  route_target: "/issues/PAY-86",
  issue: { id: 86, key: "PAY-86", title: "Handle duplicate payment callback" },
  project: { id: 1, key: "PAY", name: "Payment Platform" },
  actor: { id: 7, username: "admin", full_name: "Demo Admin" },
};

describe("InboxPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    searchParamsState.value = new URLSearchParams();
    notificationsQuery.mockReturnValue({
      data: {
        pages: [{ items: [baseNotification] }],
      },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
      hasNextPage: false,
      fetchNextPage: vi.fn(),
      isFetchingNextPage: false,
    });
    unreadCountQuery.mockReturnValue({ data: { unread_count: 3 } });
    markReadMutation.mockReturnValue({ mutate: vi.fn(), mutateAsync: vi.fn().mockResolvedValue(undefined) });
    markUnreadMutation.mockReturnValue({ mutate: vi.fn() });
    markAllReadMutation.mockReturnValue({ mutate: vi.fn(), isPending: false });
  });

  it("renders loading state", () => {
    notificationsQuery.mockReturnValueOnce({
      data: undefined,
      isLoading: true,
      isError: false,
      refetch: vi.fn(),
      hasNextPage: false,
      fetchNextPage: vi.fn(),
      isFetchingNextPage: false,
    });

    render(<InboxPage />);

    expect(screen.getByText("Notifications")).toBeInTheDocument();
    expect(screen.getByText("3 unread")).toBeInTheDocument();
  });

  it("renders error state and retries", () => {
    const refetch = vi.fn();
    notificationsQuery.mockReturnValueOnce({
      data: undefined,
      isLoading: false,
      isError: true,
      refetch,
      hasNextPage: false,
      fetchNextPage: vi.fn(),
      isFetchingNextPage: false,
    });

    render(<InboxPage />);

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(refetch).toHaveBeenCalledTimes(1);
  });

  it("renders empty unread state", () => {
    searchParamsState.value = new URLSearchParams("filter=unread");
    notificationsQuery.mockReturnValueOnce({
      data: { pages: [{ items: [] }] },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
      hasNextPage: false,
      fetchNextPage: vi.fn(),
      isFetchingNextPage: false,
    });

    render(<InboxPage />);

    expect(screen.getByText("You're all caught up")).toBeInTheDocument();
    expect(screen.getByText("No unread notifications need your attention.")).toBeInTheDocument();
  });

  it("opens unread notifications and marks them read first", async () => {
    const mutateAsync = vi.fn().mockResolvedValue(undefined);
    markReadMutation.mockReturnValueOnce({ mutate: vi.fn(), mutateAsync });

    render(<InboxPage />);

    fireEvent.click(screen.getByRole("button", { name: /Open Demo Admin assigned you to PAY-86/i }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith(11);
    });
    expect(navigate).toHaveBeenCalledWith("/issues/PAY-86");
  });

  it("changes filters and supports read, unread, and load more actions", () => {
    const fetchNextPage = vi.fn();
    const markUnread = vi.fn();
    const markAll = vi.fn();
    notificationsQuery.mockReturnValue({
      data: {
        pages: [
          {
            items: [
              { ...baseNotification, is_read: true, id: 13, title: "Viewed item" },
            ],
          },
        ],
      },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
      hasNextPage: true,
      fetchNextPage,
      isFetchingNextPage: false,
    });
    markUnreadMutation.mockReturnValueOnce({ mutate: markUnread });
    markAllReadMutation.mockReturnValueOnce({ mutate: markAll, isPending: false });

    render(<InboxPage />);

    fireEvent.click(screen.getByRole("button", { name: "Assigned" }));
    expect(setSearchParams).toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Mark unread" }));
    expect(markUnread).toHaveBeenCalledWith(13);

    fireEvent.click(screen.getByRole("button", { name: /Mark all as read/i }));
    expect(markAll).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: "Load more" }));
    expect(fetchNextPage).toHaveBeenCalledTimes(1);
  });

  it("clears the filter query for the all view and filters results by search text", () => {
    searchParamsState.value = new URLSearchParams("filter=mentions");
    notificationsQuery.mockReturnValue({
      data: {
        pages: [
          {
            items: [
              baseNotification,
              {
                ...baseNotification,
                id: 12,
                title: "Rina commented on IAM-15",
                body_preview: "Investigate Safari refresh handling",
                issue: { id: 15, key: "IAM-15", title: "Investigate Safari refresh handling" },
                project: { id: 2, key: "IAM", name: "Identity & Access" },
              },
            ],
          },
        ],
      },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
      hasNextPage: false,
      fetchNextPage: vi.fn(),
      isFetchingNextPage: false,
    });

    render(<InboxPage />);

    fireEvent.click(screen.getByRole("button", { name: "All" }));
    expect(setSearchParams).toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText("Search notifications"), {
      target: { value: "Safari" },
    });

    expect(screen.getByText("Rina commented on IAM-15")).toBeInTheDocument();
    expect(screen.queryByText("Demo Admin assigned you to PAY-86")).not.toBeInTheDocument();
  });

  it("renders the filtered empty state for non-unread views", () => {
    searchParamsState.value = new URLSearchParams("filter=mentions");
    notificationsQuery.mockReturnValueOnce({
      data: { pages: [{ items: [] }] },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
      hasNextPage: false,
      fetchNextPage: vi.fn(),
      isFetchingNextPage: false,
    });

    render(<InboxPage />);

    expect(screen.getByText("No notifications match this view right now.")).toBeInTheDocument();
  });

  it("opens already-read notifications without issuing an extra read mutation", async () => {
    const mutateAsync = vi.fn();
    markReadMutation.mockReturnValueOnce({ mutate: vi.fn(), mutateAsync });
    notificationsQuery.mockReturnValueOnce({
      data: {
        pages: [{ items: [{ ...baseNotification, id: 19, is_read: true, title: "Viewed issue" }] }],
      },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
      hasNextPage: false,
      fetchNextPage: vi.fn(),
      isFetchingNextPage: false,
    });

    render(<InboxPage />);

    fireEvent.click(screen.getByRole("button", { name: /Open Viewed issue/i }));

    await waitFor(() => {
      expect(navigate).toHaveBeenCalledWith("/issues/PAY-86");
    });
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  it("disables mark all as read when there are no unread items", () => {
    unreadCountQuery.mockReturnValueOnce({ data: { unread_count: 0 } });

    render(<InboxPage />);

    expect(screen.getByRole("button", { name: /Mark all as read/i })).toBeDisabled();
  });

  it("uses fallback preview and issue route when notification metadata is incomplete", async () => {
    notificationsQuery.mockReturnValueOnce({
      data: {
        pages: [
          {
            items: [
              {
                ...baseNotification,
                id: 44,
                route_target: null,
                title: "System updated issue",
                body_preview: null,
                project: null,
                actor: null,
                issue: { id: 44, key: null, title: null },
              },
            ],
          },
        ],
      },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
      hasNextPage: false,
      fetchNextPage: vi.fn(),
      isFetchingNextPage: false,
    });

    render(<InboxPage />);

    expect(screen.getByText("No preview available.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Open issue 44/i }));

    await waitFor(() => {
      expect(navigate).toHaveBeenCalledWith("/issues/");
    });
  });

  it("shows the loading more state while fetching the next page", () => {
    notificationsQuery.mockReturnValueOnce({
      data: {
        pages: [{ items: [baseNotification] }],
      },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
      hasNextPage: true,
      fetchNextPage: vi.fn(),
      isFetchingNextPage: true,
    });

    render(<InboxPage />);

    expect(screen.getByText("Loading more")).toBeInTheDocument();
  });
});
