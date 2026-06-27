import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import App from "./App";
import { taskApi } from "./api/tasks";
import "@testing-library/jest-dom";

// ── Mock API ─────────────────────────────────────────────────────────────────

vi.mock("./api/tasks", () => ({
  taskApi: {
    getAll: vi.fn(),
    getById: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
  },
}));

// ── Helpers ──────────────────────────────────────────────────────────────────

const makeTask = (overrides = {}) => ({
  id: 1,
  title: "Task Satu",
  description: "Deskripsi satu",
  status: "Todo" as const,
  priority: "Medium" as const,
  department: "Engineering",
  team: "Backend",
  assignee: "Alice",
  created_by: "admin",
  created_at: "2026-06-26T15:00:00Z",
  updated_at: "2026-06-26T15:00:00Z",
  due_date: "2026-12-31",
  completed_at: null,
  story_points: 3,
  estimated_hours: 8,
  actual_hours: 0,
  progress_percentage: 0,
  attachments_count: 0,
  comments_count: 0,
  watchers_count: 0,
  sprint: "Sprint-1",
  quarter: "Q1" as const,
  risk_level: "Low" as const,
  customer_impact: "None" as const,
  sla_hours: 48,
  dependencies: [],
  tags: ["backend"],
  ...overrides,
});

const paginatedResponse = (items: ReturnType<typeof makeTask>[]) => ({
  items,
  total: items.length,
  page: 1,
  size: 20,
  pages: 1,
});

// ── Tests ────────────────────────────────────────────────────────────────────

describe("TaskBoard Application", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading skeleton initially", () => {
    vi.mocked(taskApi.getAll).mockReturnValue(new Promise(() => {}));
    render(<App />);
    expect(screen.getByText(/project tracker/i)).toBeInTheDocument();
  });

  it("displays tasks after loading", async () => {
    vi.mocked(taskApi.getAll).mockResolvedValue(
      paginatedResponse([makeTask(), makeTask({ id: 2, title: "Task Dua", status: "In Progress" as const })])
    );
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText("Task Satu")).toBeInTheDocument();
      expect(screen.getByText("Task Dua")).toBeInTheDocument();
    });
  });

  it("shows error banner when API fails", async () => {
    vi.mocked(taskApi.getAll).mockRejectedValue(new Error("Network error"));
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText(/gagal memuat tasks/i)).toBeInTheDocument();
    });
  });

  it("shows all 5 kanban columns", async () => {
    vi.mocked(taskApi.getAll).mockResolvedValue(paginatedResponse([]));
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText("Todo")).toBeInTheDocument();
      expect(screen.getByText("In Progress")).toBeInTheDocument();
      expect(screen.getByText("Review")).toBeInTheDocument();
      expect(screen.getByText("Blocked")).toBeInTheDocument();
      expect(screen.getByText("Done")).toBeInTheDocument();
    });
  });

  it("can advance task status via the quick button", async () => {
    vi.mocked(taskApi.getAll).mockResolvedValue(
      paginatedResponse([makeTask()])
    );
    vi.mocked(taskApi.update).mockResolvedValue(makeTask({ status: "In Progress" as const }));
    render(<App />);
    await screen.findByText("Task Satu");

    const advBtn = screen.getByText("→ In Progress");
    fireEvent.click(advBtn);
    await waitFor(() => {
      expect(taskApi.update).toHaveBeenCalledWith(1, { status: "In Progress" });
    });
  });

  it("can delete a task with confirmation", async () => {
    vi.mocked(taskApi.getAll).mockResolvedValue(paginatedResponse([makeTask()]));
    vi.mocked(taskApi.delete).mockResolvedValue({ data: {} });
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<App />);
    await screen.findByText("Task Satu");

    const deleteBtn = screen.getByTitle("Hapus");
    fireEvent.click(deleteBtn);

    expect(confirmSpy).toHaveBeenCalled();
    await waitFor(() => {
      expect(taskApi.delete).toHaveBeenCalledWith(1);
    });
  });

  it("shows pagination controls when pages > 1", async () => {
    vi.mocked(taskApi.getAll).mockResolvedValue({
      items: [makeTask()],
      total: 40,
      page: 1,
      size: 20,
      pages: 2,
    });
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText(/prev/i)).toBeInTheDocument();
      expect(screen.getByText(/next/i)).toBeInTheDocument();
    });
  });

  it("does not show pagination when on single page", async () => {
    vi.mocked(taskApi.getAll).mockResolvedValue(paginatedResponse([makeTask()]));
    render(<App />);
    await waitFor(() => {
      expect(screen.queryByText(/prev/i)).not.toBeInTheDocument();
    });
  });

  it("opens create form and validates empty title", async () => {
    vi.mocked(taskApi.getAll).mockResolvedValue(paginatedResponse([]));
    render(<App />);
    await screen.findByText("+ Tambah Task Baru");

    fireEvent.click(screen.getByText("+ Tambah Task Baru"));
    fireEvent.click(screen.getByText("Buat Task"));
    expect(screen.getByText("Judul tidak boleh kosong.")).toBeInTheDocument();
  });

  it("can cancel the create form", async () => {
    vi.mocked(taskApi.getAll).mockResolvedValue(paginatedResponse([]));
    render(<App />);
    await screen.findByText("+ Tambah Task Baru");

    fireEvent.click(screen.getByText("+ Tambah Task Baru"));
    expect(screen.getByText("Buat Task")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Batal"));
    expect(screen.queryByText("Buat Task")).not.toBeInTheDocument();
  });

  it("validates missing department, team, assignee, or created_by", async () => {
    vi.mocked(taskApi.getAll).mockResolvedValue(paginatedResponse([]));
    render(<App />);
    await screen.findByText("+ Tambah Task Baru");

    fireEvent.click(screen.getByText("+ Tambah Task Baru"));
    
    // Fill title
    const titleInput = screen.getByPlaceholderText("Judul task... *");
    fireEvent.change(titleInput, { target: { value: "Task Baru" } });

    fireEvent.click(screen.getByText("Buat Task"));
    expect(screen.getByText("Department, team, assignee, dan created by wajib diisi.")).toBeInTheDocument();
  });

  it("validates missing sprint", async () => {
    vi.mocked(taskApi.getAll).mockResolvedValue(paginatedResponse([]));
    render(<App />);
    await screen.findByText("+ Tambah Task Baru");

    fireEvent.click(screen.getByText("+ Tambah Task Baru"));
    
    // Fill title
    fireEvent.change(screen.getByPlaceholderText("Judul task... *"), { target: { value: "Task Baru" } });
    fireEvent.change(screen.getByPlaceholderText("Department *"), { target: { value: "Engineering" } });
    fireEvent.change(screen.getByPlaceholderText("Team *"), { target: { value: "Backend" } });
    fireEvent.change(screen.getByPlaceholderText("Assignee *"), { target: { value: "Alice" } });
    fireEvent.change(screen.getByPlaceholderText("Created by *"), { target: { value: "Admin" } });

    fireEvent.click(screen.getByText("Buat Task"));
    expect(screen.getByText("Sprint wajib diisi.")).toBeInTheDocument();
  });

  it("successfully creates a task with all fields", async () => {
    vi.mocked(taskApi.getAll).mockResolvedValue(paginatedResponse([]));
    const mockCreated = makeTask({ id: 99, title: "New Task" });
    vi.mocked(taskApi.create).mockResolvedValue(mockCreated);

    render(<App />);
    await screen.findByText("+ Tambah Task Baru");

    fireEvent.click(screen.getByText("+ Tambah Task Baru"));
    
    fireEvent.change(screen.getByPlaceholderText("Judul task... *"), { target: { value: "New Task" } });
    fireEvent.change(screen.getByPlaceholderText("Department *"), { target: { value: "Engineering" } });
    fireEvent.change(screen.getByPlaceholderText("Team *"), { target: { value: "Backend" } });
    fireEvent.change(screen.getByPlaceholderText("Assignee *"), { target: { value: "Alice" } });
    fireEvent.change(screen.getByPlaceholderText("Created by *"), { target: { value: "Admin" } });
    fireEvent.change(screen.getByPlaceholderText("Sprint (e.g. Sprint-1) *"), { target: { value: "Sprint-1" } });
    fireEvent.change(screen.getByPlaceholderText("Tags (comma-separated, max 4): security, automation"), { target: { value: "tag1, tag2" } });

    fireEvent.click(screen.getByText("Buat Task"));

    await waitFor(() => {
      expect(taskApi.create).toHaveBeenCalled();
      expect(screen.getByText("New Task")).toBeInTheDocument();
    });
  });

  it("handles pagination clicks", async () => {
    vi.mocked(taskApi.getAll).mockResolvedValue({
      items: [makeTask()],
      total: 40,
      page: 1,
      size: 20,
      pages: 2,
    });
    render(<App />);
    await screen.findByText("Task Satu");

    const nextBtn = screen.getByText("Next →");
    fireEvent.click(nextBtn);

    await waitFor(() => {
      expect(taskApi.getAll).toHaveBeenLastCalledWith({ page: 2, size: 20 });
    });

    const prevBtn = screen.getByText("← Prev");
    fireEvent.click(prevBtn);

    await waitFor(() => {
      expect(taskApi.getAll).toHaveBeenLastCalledWith({ page: 1, size: 20 });
    });
  });

  it("handles deletion cancellation", async () => {
    vi.mocked(taskApi.getAll).mockResolvedValue(paginatedResponse([makeTask()]));
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);

    render(<App />);
    await screen.findByText("Task Satu");

    const deleteBtn = screen.getByTitle("Hapus");
    fireEvent.click(deleteBtn);

    expect(confirmSpy).toHaveBeenCalled();
    expect(taskApi.delete).not.toHaveBeenCalled();
  });

  it("handles deletion failure rollback", async () => {
    vi.mocked(taskApi.getAll).mockResolvedValue(paginatedResponse([makeTask()]));
    vi.mocked(taskApi.delete).mockRejectedValue(new Error("Database error"));
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<App />);
    await screen.findByText("Task Satu");

    const deleteBtn = screen.getByTitle("Hapus");
    fireEvent.click(deleteBtn);

    await waitFor(() => {
      expect(taskApi.delete).toHaveBeenCalledWith(1);
    });
    // Wait for hook to catch error and call getAll to revert/rollback
    await waitFor(() => {
      expect(taskApi.getAll).toHaveBeenCalledTimes(2);
    });
  });

  it("updates all select fields in create form", async () => {
    vi.mocked(taskApi.getAll).mockResolvedValue(paginatedResponse([]));
    vi.mocked(taskApi.create).mockResolvedValue(makeTask());
    render(<App />);
    await screen.findByText("+ Tambah Task Baru");
    fireEvent.click(screen.getByText("+ Tambah Task Baru"));

    fireEvent.change(screen.getByPlaceholderText("Judul task... *"), { target: { value: "A" } });
    fireEvent.change(screen.getByPlaceholderText("Deskripsi (opsional)..."), { target: { value: "Deskripsi Baru" } });
    fireEvent.change(screen.getByPlaceholderText("Department *"), { target: { value: "B" } });
    fireEvent.change(screen.getByPlaceholderText("Team *"), { target: { value: "C" } });
    fireEvent.change(screen.getByPlaceholderText("Assignee *"), { target: { value: "D" } });
    fireEvent.change(screen.getByPlaceholderText("Created by *"), { target: { value: "E" } });
    fireEvent.change(screen.getByPlaceholderText("Sprint (e.g. Sprint-1) *"), { target: { value: "F" } });

    // We can also target by their ids
    const statusSelect = document.getElementById("create-status") as HTMLSelectElement;
    const prioritySelect = document.getElementById("create-priority") as HTMLSelectElement;
    const spSelect = document.getElementById("create-story-points") as HTMLSelectElement;
    const quarterSelect = document.getElementById("create-quarter") as HTMLSelectElement;
    const riskSelect = document.getElementById("create-risk-level") as HTMLSelectElement;
    const impactSelect = document.getElementById("create-customer-impact") as HTMLSelectElement;
    const slaSelect = document.getElementById("create-sla-hours") as HTMLSelectElement;
    const dueDateInput = document.getElementById("create-due-date") as HTMLInputElement;
    const estHoursInput = document.getElementById("create-estimated-hours") as HTMLInputElement;

    fireEvent.change(statusSelect, { target: { value: "In Progress" } });
    fireEvent.change(prioritySelect, { target: { value: "Critical" } });
    fireEvent.change(spSelect, { target: { value: "5" } });
    fireEvent.change(quarterSelect, { target: { value: "Q2" } });
    fireEvent.change(riskSelect, { target: { value: "High" } });
    fireEvent.change(impactSelect, { target: { value: "High" } });
    fireEvent.change(slaSelect, { target: { value: "72" } });
    fireEvent.change(dueDateInput, { target: { value: "2026-12-31" } });
    fireEvent.change(estHoursInput, { target: { value: "12" } });

    // Submit via Enter key
    const titleInput = screen.getByPlaceholderText("Judul task... *");
    fireEvent.keyDown(titleInput, { key: "Enter", code: "Enter" });

    await waitFor(() => {
      expect(taskApi.create).toHaveBeenCalled();
    });
  });

  it("renders task with progress bar, invalid priority, and updates other tasks", async () => {
    const task1 = makeTask({ id: 1, title: "Task 1", progress_percentage: 50, priority: "Invalid" as any });
    const task2 = makeTask({ id: 2, title: "Task 2" });
    vi.mocked(taskApi.getAll).mockResolvedValue(paginatedResponse([task1, task2]));
    vi.mocked(taskApi.update).mockResolvedValue(makeTask({ id: 1, title: "Task 1 Updated", progress_percentage: 60 }));

    render(<App />);
    await screen.findByText("Task 1");
    await screen.findByText("Task 2");
    
    // Check progress percentage text
    expect(screen.getByText("50%")).toBeInTheDocument();

    // Check status advance updates and triggers tasks mapping
    const advBtn = screen.getAllByText("→ In Progress")[0];
    fireEvent.click(advBtn);

    await waitFor(() => {
      expect(taskApi.update).toHaveBeenCalled();
    });
  });

  it("renders Done status task and overdue task", async () => {
    const overdueTask = makeTask({ id: 10, title: "Overdue Task", due_date: "2020-01-01" });
    const doneTask = makeTask({ id: 20, title: "Done Task", status: "Done" as const });
    vi.mocked(taskApi.getAll).mockResolvedValue(paginatedResponse([overdueTask, doneTask]));

    render(<App />);
    await screen.findByText("Overdue Task");
    await screen.findByText("Done Task");

    // Overdue task should have overdue color class or style
    const overdueLabel = screen.getByText("📅 1 Jan 2020");
    expect(overdueLabel).toHaveClass("text-red-500");
  });

  it("handles creation API error", async () => {
    vi.mocked(taskApi.getAll).mockResolvedValue(paginatedResponse([]));
    vi.mocked(taskApi.create).mockRejectedValue(new Error("API Error"));

    render(<App />);
    await screen.findByText("+ Tambah Task Baru");
    fireEvent.click(screen.getByText("+ Tambah Task Baru"));

    fireEvent.change(screen.getByPlaceholderText("Judul task... *"), { target: { value: "Fail Task" } });
    fireEvent.change(screen.getByPlaceholderText("Department *"), { target: { value: "B" } });
    fireEvent.change(screen.getByPlaceholderText("Team *"), { target: { value: "C" } });
    fireEvent.change(screen.getByPlaceholderText("Assignee *"), { target: { value: "D" } });
    fireEvent.change(screen.getByPlaceholderText("Created by *"), { target: { value: "E" } });
    fireEvent.change(screen.getByPlaceholderText("Sprint (e.g. Sprint-1) *"), { target: { value: "F" } });

    fireEvent.click(screen.getByText("Buat Task"));

    await waitFor(() => {
      expect(screen.getByText("Gagal membuat task. Coba lagi.")).toBeInTheDocument();
    });
  });
});
