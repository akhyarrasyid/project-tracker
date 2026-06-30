import "@testing-library/jest-dom";
import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

const {
  navigate,
  setSearchParams,
  issuePanel,
  taskList,
  taskCalendar,
  boardQuery,
  issueQuery,
  quickAddOpen,
  taskCreate,
  issueMove,
} = vi.hoisted(() => ({
  navigate: vi.fn(),
  setSearchParams: vi.fn(),
  issuePanel: vi.fn(({ issueKey }: { issueKey?: string }) => <div>Issue panel {issueKey ?? "none"}</div>),
  taskList: vi.fn(({ onTaskClick }: { onTaskClick: (task: any) => void }) => (
    <button type="button" onClick={() => onTaskClick({ id: 12, key: "PAY-12", title: "Handle duplicate callback" })}>
      Open from list
    </button>
  )),
  taskCalendar: vi.fn(({ onTaskClick }: { onTaskClick: (task: any) => void }) => (
    <button type="button" onClick={() => onTaskClick({ key: "PAY-12" })}>
      Open from calendar
    </button>
  )),
  boardQuery: vi.fn(),
  issueQuery: vi.fn(),
  quickAddOpen: vi.fn(),
  taskCreate: vi.fn(),
  issueMove: vi.fn(),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => navigate,
    useParams: () => ({ projectKey: "PAY", issueKey: "PAY-12" }),
    useSearchParams: () => [new URLSearchParams("issue=PAY-12"), setSearchParams],
  };
});

vi.mock("../features/issues/hooks/useBoardQuery", () => ({
  useBoardQuery: boardQuery,
}));

vi.mock("../features/issues/hooks/useIssueQuery", () => ({
  useIssueQuery: issueQuery,
}));

vi.mock("../features/issues/components/IssueDetailPanel", () => ({
  IssueDetailPanel: issuePanel,
}));

vi.mock("../components/TaskTaskList", () => ({
  TaskTaskList: taskList,
}));

vi.mock("../components/TaskCalendar", () => ({
  TaskCalendar: taskCalendar,
}));

vi.mock("../api/tasks", () => ({
  taskApi: {
    create: taskCreate,
  },
}));

vi.mock("../api/issues", () => ({
  issueApi: {
    move: issueMove,
  },
}));

vi.mock("../components/CreateTaskForm", async () => {
  const React = await vi.importActual<typeof import("react")>("react");
  return {
    CreateTaskForm: React.forwardRef(function MockCreateTaskForm(
      props: { onCreate: (payload: any, projectId: number) => Promise<unknown>; currentProjectId?: number | null },
      ref,
    ) {
      React.useImperativeHandle(ref, () => ({
        open: quickAddOpen,
      }));
      return (
        <button type="button" onClick={() => props.onCreate({ title: "Quick add" }, props.currentProjectId ?? 0)}>
          Quick add form
        </button>
      );
    }),
  };
});

vi.mock("../components/KanbanColumn", () => ({
  KanbanColumn: ({
    status,
    tasks,
    totalCount,
    onAddIssue,
    renderTask,
    extra,
  }: {
    status: string;
    tasks: any[];
    totalCount: number;
    onAddIssue?: () => void;
    renderTask: (task: any) => React.ReactNode;
    extra?: React.ReactNode;
  }) => (
    <section>
      <div>{status}</div>
      <div>{totalCount}</div>
      <button type="button" onClick={onAddIssue}>
        Add issue to {status}
      </button>
      {tasks.map((task) => renderTask(task))}
      {extra}
    </section>
  ),
}));

vi.mock("../components/TaskCard", () => ({
  TaskCard: ({ task, onTaskClick }: { task: any; onTaskClick: (task: any) => void }) => (
    <button type="button" onClick={() => onTaskClick(task)}>
      {task.key}
    </button>
  ),
}));

vi.mock("@dnd-kit/core", () => ({
  DndContext: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DragOverlay: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  PointerSensor: class {},
  KeyboardSensor: class {},
  useSensor: () => ({}),
  useSensors: () => [],
  closestCenter: vi.fn(),
}));

vi.mock("@dnd-kit/sortable", () => ({
  SortableContext: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  useSortable: () => ({
    attributes: {},
    listeners: {},
    setNodeRef: vi.fn(),
    transform: null,
    transition: undefined,
    isDragging: false,
  }),
  sortableKeyboardCoordinates: vi.fn(),
  verticalListSortingStrategy: {},
}));

vi.mock("@dnd-kit/utilities", () => ({
  CSS: {
    Transform: {
      toString: () => "",
    },
  },
}));

import { CalendarPage } from "./CalendarPage";
import { IssuePage } from "./IssuePage";
import { IssuesPage } from "./IssuesPage";
import { MyIssuesPage } from "./MyIssuesPage";
import { ProjectBoardPage } from "./ProjectBoardPage";

vi.mock("../contexts/useAuth", () => ({
  useAuth: () => ({
    user: { id: 7 },
  }),
}));

vi.mock("../features/issues/hooks/useMyIssuesQuery", () => ({
  useMyIssuesQuery: () => ({
    isLoading: false,
    data: {
      items: [{ id: 1, key: "PAY-1", title: "Handle duplicate callback", status: "Todo", due_date: "2026-07-05" }],
    },
  }),
}));

describe("route pages", () => {
  const renderWithQueryClient = (ui: React.ReactNode) => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
  };

  beforeEach(() => {
    vi.clearAllMocks();
    boardQuery.mockReturnValue({
      data: {
        columns: {
          Todo: { status: "Todo", items: [{ id: 12, key: "PAY-12", title: "Handle duplicate callback", status: "Todo", version: 1 }], total_count: 1 },
          "In Progress": { status: "In Progress", items: [], total_count: 0 },
          Review: { status: "Review", items: [], total_count: 0 },
          Done: { status: "Done", items: [], total_count: 0 },
        },
      },
      projectQuery: {
        data: { id: 3 },
      },
    });
    taskCreate.mockResolvedValue({ id: 33, key: "PAY-33" });
  });

  it("renders MyIssuesPage and navigates to issue detail", () => {
    render(<MyIssuesPage />);

    fireEvent.click(screen.getByRole("button", { name: /Handle duplicate callback/i }));
    expect(navigate).toHaveBeenCalledWith("/issues/PAY-1");
  });

  it("renders IssuesPage and updates search params on click", () => {
    render(<IssuesPage />);

    fireEvent.click(screen.getByRole("button", { name: "Open from list" }));
    expect(setSearchParams).toHaveBeenCalled();
    expect(screen.getByText("Issue panel PAY-12")).toBeInTheDocument();
  });

  it("renders CalendarPage and opens an issue from the calendar", () => {
    render(<CalendarPage />);

    fireEvent.click(screen.getByRole("button", { name: "Open from calendar" }));
    expect(navigate).toHaveBeenCalledWith("/issues/PAY-12");
  });

  it("renders IssuePage and navigates back", () => {
    render(<IssuePage />);

    fireEvent.click(screen.getByRole("button", { name: /Back/i }));
    expect(navigate).toHaveBeenCalledWith(-1);
    expect(screen.getByText("Issue panel PAY-12")).toBeInTheDocument();
  });

  it("renders ProjectBoardPage totals, quick add, and board issue open", async () => {
    renderWithQueryClient(<ProjectBoardPage />);

    expect(screen.getByText("1 issues")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Add issue to Todo" }));
    expect(quickAddOpen).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: "PAY-12" }));
    expect(setSearchParams).toHaveBeenCalled();

    fireEvent.click(screen.getAllByRole("button", { name: "Quick add form" })[0]);
    expect(taskCreate).toHaveBeenCalledWith({ title: "Quick add" }, 3);
  });
});
