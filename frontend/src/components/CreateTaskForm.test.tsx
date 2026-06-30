import "@testing-library/jest-dom";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createRef } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { getDepartments, getTeams, getProjects, getUsers } = vi.hoisted(() => ({
  getDepartments: vi.fn(),
  getTeams: vi.fn(),
  getProjects: vi.fn(),
  getUsers: vi.fn(),
}));

vi.mock("../api/meta", () => ({
  metaApi: {
    getDepartments,
    getTeams,
    getProjects,
    getUsers,
  },
}));

import { CreateTaskForm, type CreateTaskFormHandle } from "./CreateTaskForm";

describe("CreateTaskForm", () => {
  const onCreate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    getDepartments.mockResolvedValue([{ id: 1, name: "Engineering" }]);
    getTeams.mockResolvedValue([{ id: 2, name: "Platform Team" }]);
    getProjects.mockResolvedValue([{ id: 3, name: "Payment Platform", key: "PAY" }]);
    getUsers.mockResolvedValue([{ id: 4, full_name: "Amanda", email: "amanda@tracker.dev" }]);
    onCreate.mockResolvedValue({ id: 12 });
  });

  it("opens from the trigger button and validates required fields", async () => {
    render(<CreateTaskForm onCreate={onCreate} />);

    fireEvent.click(screen.getByRole("button", { name: /\+ Tambah Task Baru/i }));
    expect(await screen.findByText("Buat Task Baru")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Buat Task" }));
    expect(await screen.findByText("Judul task wajib diisi")).toBeInTheDocument();
  });

  it("supports imperative open and creates a task with cascaded selections", async () => {
    const ref = createRef<CreateTaskFormHandle>();
    render(<CreateTaskForm ref={ref} onCreate={onCreate} initialStatus="Review" />);

    act(() => {
      ref.current?.open();
    });

    expect(await screen.findByText("Buat Task Baru")).toBeInTheDocument();
    await waitFor(() => {
      expect(getDepartments).toHaveBeenCalledTimes(1);
    });

    fireEvent.change(screen.getByLabelText("Judul Task *"), { target: { value: "Handle duplicate callback" } });
    fireEvent.change(screen.getByLabelText("Deskripsi"), { target: { value: "Investigate retries" } });

    fireEvent.change(screen.getByLabelText("Departemen"), { target: { value: "1" } });
    await waitFor(() => expect(getTeams).toHaveBeenCalledWith(1));

    fireEvent.change(screen.getByLabelText("Tim"), { target: { value: "2" } });
    await waitFor(() => expect(getProjects).toHaveBeenCalledWith(2));

    fireEvent.change(screen.getByLabelText("Proyek *"), { target: { value: "3" } });
    await waitFor(() => expect(getUsers).toHaveBeenCalledWith(3));

    fireEvent.change(screen.getByLabelText("Assignee"), { target: { value: "4" } });
    fireEvent.change(screen.getByLabelText("Tags"), { target: { value: "payments, backend" } });
    fireEvent.click(screen.getByRole("button", { name: "Buat Task" }));

    await waitFor(() => {
      expect(onCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Handle duplicate callback",
          description: "Investigate retries",
          status: "Review",
          assignee_id: 4,
          tags: ["payments", "backend"],
        }),
        3,
      );
    });
  });

  it("loads assignees for the current project and handles request failures", async () => {
    onCreate.mockRejectedValue({
      response: {
        data: {
          detail: "Gagal membuat task",
        },
      },
    });

    render(<CreateTaskForm onCreate={onCreate} currentProjectId={9} />);

    fireEvent.click(screen.getByRole("button", { name: /\+ Tambah Task Baru/i }));
    expect(await screen.findByText("Buat Task Baru")).toBeInTheDocument();
    await waitFor(() => expect(getUsers).toHaveBeenCalledWith(9));

    fireEvent.change(screen.getByLabelText("Judul Task *"), { target: { value: "Quick add issue" } });
    fireEvent.click(screen.getByRole("button", { name: "Buat Task" }));

    expect(await screen.findByText("Gagal membuat task")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Batal" }));
    await waitFor(() => {
      expect(screen.queryByText("Buat Task Baru")).not.toBeInTheDocument();
    });
  });
});
