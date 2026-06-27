import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import App from "./App";
import { taskApi } from "./api/tasks";
import "@testing-library/jest-dom";

// Mock the API client
vi.mock("./api/tasks", () => {
  return {
    taskApi: {
      getAll: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
    },
  };
});

describe("TaskBoard Frontend Application", () => {
  const mockTasks = [
    {
      id: 1,
      title: "Task Satu",
      description: "Deskripsi satu",
      status: "Todo" as const,
      created_at: "2026-06-26T15:00:00Z",
      updated_at: "2026-06-26T15:00:00Z",
    },
    {
      id: 2,
      title: "Task Dua",
      description: "Deskripsi dua",
      status: "In Progress" as const,
      created_at: "2026-06-26T15:00:00Z",
      updated_at: "2026-06-26T15:00:00Z",
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should show loading state and then display the list of tasks", async () => {
    vi.mocked(taskApi.getAll).mockResolvedValue(mockTasks);

    render(<App />);

    // Initially loading state is shown
    expect(screen.getByText(/tasks/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Task Satu")).toBeInTheDocument();
      expect(screen.getByText("Task Dua")).toBeInTheDocument();
    });
  });

  it("should handle adding a new task", async () => {
    vi.mocked(taskApi.getAll).mockResolvedValue(mockTasks);
    vi.mocked(taskApi.create).mockResolvedValue({
      id: 3,
      title: "Task Tiga",
      description: "Deskripsi tiga",
      status: "Todo" as const,
      created_at: "2026-06-26T15:00:00Z",
      updated_at: "2026-06-26T15:00:00Z",
    });

    render(<App />);

    // Wait for initial load
    await screen.findByText("Task Satu");

    // Click "+ Tambah Task Baru"
    const addBtn = screen.getByText("+ Tambah Task Baru");
    fireEvent.click(addBtn);

    // Fill form
    const titleInput = screen.getByPlaceholderText("Judul task...");
    const descInput = screen.getByPlaceholderText("Deskripsi (opsional)...");
    fireEvent.change(titleInput, { target: { value: "Task Tiga" } });
    fireEvent.change(descInput, { target: { value: "Deskripsi tiga" } });

    // Submit
    const submitBtn = screen.getByText("Buat Task");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(taskApi.create).toHaveBeenCalledWith({
        title: "Task Tiga",
        description: "Deskripsi tiga",
        status: "Todo",
      });
      expect(screen.getByText("Task Tiga")).toBeInTheDocument();
    });
  });

  it("should handle updating task status", async () => {
    vi.mocked(taskApi.getAll).mockResolvedValue(mockTasks);
    vi.mocked(taskApi.update).mockResolvedValue({
      id: 1,
      title: "Task Satu",
      description: "Deskripsi satu",
      status: "In Progress" as const,
      created_at: "2026-06-26T15:00:00Z",
      updated_at: "2026-06-26T15:00:00Z",
    });

    render(<App />);
    await screen.findByText("Task Satu");

    // Click quick advance button "→ Pindah ke In Progress"
    const advanceBtn = screen.getByText("→ Pindah ke In Progress");
    fireEvent.click(advanceBtn);

    await waitFor(() => {
      expect(taskApi.update).toHaveBeenCalledWith(1, { status: "In Progress" });
    });
  });

  it("should handle deleting a task with confirmation", async () => {
    vi.mocked(taskApi.getAll).mockResolvedValue(mockTasks);
    vi.mocked(taskApi.delete).mockResolvedValue({ data: {} });
    
    // Mock window.confirm
    const confirmSpy = vi.spyOn(window, "confirm").mockImplementation(() => true);

    render(<App />);
    await screen.findByText("Task Satu");

    // Click delete button
    const deleteBtn = screen.getAllByTitle("Hapus")[0];
    fireEvent.click(deleteBtn);

    expect(confirmSpy).toHaveBeenCalled();
    await waitFor(() => {
      expect(taskApi.delete).toHaveBeenCalledWith(1);
      expect(screen.queryByText("Task Satu")).not.toBeInTheDocument();
    });
  });

  it("should handle editing a task and saving it", async () => {
    vi.mocked(taskApi.getAll).mockResolvedValue(mockTasks);
    vi.mocked(taskApi.update).mockResolvedValue({
      id: 1,
      title: "Task Satu Baru",
      description: "Deskripsi satu baru",
      status: "Todo" as const,
      created_at: "2026-06-26T15:00:00Z",
      updated_at: "2026-06-26T15:00:00Z",
    });

    render(<App />);
    await screen.findByText("Task Satu");

    // Click Edit button
    const editBtn = screen.getAllByTitle("Edit")[0];
    fireEvent.click(editBtn);

    // Edit inputs are now visible
    const titleInput = screen.getByPlaceholderText("Judul task...");
    const descInput = screen.getByPlaceholderText("Deskripsi (opsional)...");
    
    fireEvent.change(titleInput, { target: { value: "Task Satu Baru" } });
    fireEvent.change(descInput, { target: { value: "Deskripsi satu baru" } });

    // Click Save
    const saveBtn = screen.getByText("Simpan");
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(taskApi.update).toHaveBeenCalledWith(1, {
        title: "Task Satu Baru",
        description: "Deskripsi satu baru",
      });
      expect(screen.getByText("Task Satu Baru")).toBeInTheDocument();
      expect(screen.getByText("Deskripsi satu baru")).toBeInTheDocument();
    });
  });

  it("should handle editing a task and canceling it", async () => {
    vi.mocked(taskApi.getAll).mockResolvedValue(mockTasks);

    render(<App />);
    await screen.findByText("Task Satu");

    // Click Edit
    const editBtn = screen.getAllByTitle("Edit")[0];
    fireEvent.click(editBtn);

    // Click Batal
    const cancelBtn = screen.getByText("Batal");
    fireEvent.click(cancelBtn);

    expect(screen.getByText("Task Satu")).toBeInTheDocument();
  });

  it("should handle changing task status via select dropdown", async () => {
    vi.mocked(taskApi.getAll).mockResolvedValue(mockTasks);
    vi.mocked(taskApi.update).mockResolvedValue({
      id: 1,
      title: "Task Satu",
      description: "Deskripsi satu",
      status: "Done" as const,
      created_at: "2026-06-26T15:00:00Z",
      updated_at: "2026-06-26T15:00:00Z",
    });

    render(<App />);
    await screen.findByText("Task Satu");

    // Find select element for Task Satu status (default Todo)
    const select = screen.getAllByRole("combobox")[0];
    fireEvent.change(select, { target: { value: "Done" } });

    await waitFor(() => {
      expect(taskApi.update).toHaveBeenCalledWith(1, { status: "Done" });
    });
  });

  it("should validate empty title when creating a task", async () => {
    vi.mocked(taskApi.getAll).mockResolvedValue(mockTasks);

    render(<App />);
    await screen.findByText("Task Satu");

    // Open form
    const addBtn = screen.getByText("+ Tambah Task Baru");
    fireEvent.click(addBtn);

    // Leave title empty and click Buat Task
    const submitBtn = screen.getByText("Buat Task");
    fireEvent.click(submitBtn);

    // Expect validation message
    expect(screen.getByText("Judul tidak boleh kosong.")).toBeInTheDocument();
  });

  it("should handle task creation failure", async () => {
    vi.mocked(taskApi.getAll).mockResolvedValue(mockTasks);
    vi.mocked(taskApi.create).mockRejectedValueOnce(new Error("Server error"));

    render(<App />);
    await screen.findByText("Task Satu");

    // Open form
    const addBtn = screen.getByText("+ Tambah Task Baru");
    fireEvent.click(addBtn);

    // Fill form
    const titleInput = screen.getByPlaceholderText("Judul task...");
    fireEvent.change(titleInput, { target: { value: "Task Gagal" } });

    // Submit
    const submitBtn = screen.getByText("Buat Task");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText("Gagal membuat task. Coba lagi.")).toBeInTheDocument();
    });
  });

  it("should handle canceling task creation", async () => {
    vi.mocked(taskApi.getAll).mockResolvedValue(mockTasks);

    render(<App />);
    await screen.findByText("Task Satu");

    // Open form
    const addBtn = screen.getByText("+ Tambah Task Baru");
    fireEvent.click(addBtn);

    // Cancel form
    const cancelBtn = screen.getByText("Batal");
    fireEvent.click(cancelBtn);

    expect(screen.getByText("+ Tambah Task Baru")).toBeInTheDocument();
  });

  it("should submit form on Enter key down", async () => {
    vi.mocked(taskApi.getAll).mockResolvedValue(mockTasks);
    vi.mocked(taskApi.create).mockResolvedValue({
      id: 4,
      title: "Task Enter",
      description: "",
      status: "Todo" as const,
      created_at: "2026-06-26T15:00:00Z",
      updated_at: "2026-06-26T15:00:00Z",
    });

    render(<App />);
    await screen.findByText("Task Satu");

    // Open form
    const addBtn = screen.getByText("+ Tambah Task Baru");
    fireEvent.click(addBtn);

    // Fill title and press Enter
    const titleInput = screen.getByPlaceholderText("Judul task...");
    fireEvent.change(titleInput, { target: { value: "Task Enter" } });
    fireEvent.keyDown(titleInput, { key: "Enter", code: "Enter" });

    await waitFor(() => {
      expect(taskApi.create).toHaveBeenCalled();
    });
  });
});


