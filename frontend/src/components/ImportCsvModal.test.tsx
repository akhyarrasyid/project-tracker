import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ImportCsvModal } from "./ImportCsvModal";
import { API_BASE_URL } from "../api/client";
import "@testing-library/jest-dom";

describe("ImportCsvModal Component", () => {
  const onClose = vi.fn();
  const onSuccess = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock window fetch
    window.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: true,
        blob: () => Promise.resolve(new Blob(["mock,csv,data"], { type: "text/csv" })),
      } as any)
    );
    // Mock URL object methods
    window.URL.createObjectURL = vi.fn(() => "mock-url");
    window.URL.revokeObjectURL = vi.fn();
  });

  it("does not render when isOpen is false", () => {
    const { container } = render(
      <ImportCsvModal isOpen={false} onClose={onClose} onSuccess={onSuccess} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders correct title and close buttons when open", () => {
    render(<ImportCsvModal isOpen={true} onClose={onClose} onSuccess={onSuccess} />);
    
    expect(screen.getByText("Impor Task (CSV)")).toBeInTheDocument();
    expect(screen.getByText("Gunakan template standar kami agar format data sesuai.")).toBeInTheDocument();
    
    const cancelBtn = screen.getByText("Batal");
    expect(cancelBtn).toBeInTheDocument();
    
    fireEvent.click(cancelBtn);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("triggers template download on button click", async () => {
    render(<ImportCsvModal isOpen={true} onClose={onClose} onSuccess={onSuccess} />);
    
    const downloadBtn = screen.getByText("Unduh Template");
    fireEvent.click(downloadBtn);
    
    expect(window.fetch).toHaveBeenCalledWith(
      `${API_BASE_URL}/api/v1/tasks/import-template`,
      expect.any(Object)
    );
  });

  it("handles template download failure", async () => {
    window.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: false,
      } as any)
    );
    
    render(<ImportCsvModal isOpen={true} onClose={onClose} onSuccess={onSuccess} />);
    const downloadBtn = screen.getByText("Unduh Template");
    fireEvent.click(downloadBtn);

    await waitFor(() => {
      expect(screen.getByText("Gagal mengunduh template")).toBeInTheDocument();
    });
  });

  it("handles file selection via input change", async () => {
    render(<ImportCsvModal isOpen={true} onClose={onClose} onSuccess={onSuccess} />);
    
    const file = new File(["title,project_key\nTask 1,PRJ"], "tasks.csv", { type: "text/csv" });
    const input = document.querySelector("input[type='file']") as HTMLInputElement;
    expect(input).not.toBeNull();
    
    fireEvent.change(input, { target: { files: [file] } });
    
    await waitFor(() => {
      expect(screen.getByText("tasks.csv")).toBeInTheDocument();
    });
  });

  it("allows removing selected file", async () => {
    render(<ImportCsvModal isOpen={true} onClose={onClose} onSuccess={onSuccess} />);
    
    const file = new File(["title,project_key\nTask 1,PRJ"], "tasks.csv", { type: "text/csv" });
    const input = document.querySelector("input[type='file']") as HTMLInputElement;
    
    fireEvent.change(input, { target: { files: [file] } });
    
    await waitFor(() => {
      expect(screen.getByText("tasks.csv")).toBeInTheDocument();
    });

    const removeBtn = document.querySelector(".bg-slate-50.border.border-slate-100 button") as HTMLButtonElement;
    expect(removeBtn).not.toBeNull();
    fireEvent.click(removeBtn);

    await waitFor(() => {
      expect(screen.queryByText("tasks.csv")).not.toBeInTheDocument();
    });
  });

  it("handles drag events", () => {
    render(<ImportCsvModal isOpen={true} onClose={onClose} onSuccess={onSuccess} />);
    
    const dropzone = screen.getByText("Tarik & lepas file CSV di sini, atau klik untuk memilih").parentElement?.parentElement as HTMLElement;
    
    fireEvent.dragEnter(dropzone);
    fireEvent.dragOver(dropzone);
    fireEvent.dragLeave(dropzone);
    
    expect(dropzone).toBeInTheDocument();
  });

  it("handles file drop", async () => {
    render(<ImportCsvModal isOpen={true} onClose={onClose} onSuccess={onSuccess} />);
    const dropzone = screen.getByText("Tarik & lepas file CSV di sini, atau klik untuk memilih").parentElement?.parentElement as HTMLElement;
    
    const file = new File(["title,project_key\nTask 1,PRJ"], "tasks.csv", { type: "text/csv" });
    
    fireEvent.drop(dropzone, {
      dataTransfer: {
        files: [file],
      },
    });
    
    await waitFor(() => {
      expect(screen.getByText("tasks.csv")).toBeInTheDocument();
    });
  });

  it("handles drop of non-csv files", async () => {
    render(<ImportCsvModal isOpen={true} onClose={onClose} onSuccess={onSuccess} />);
    const dropzone = screen.getByText("Tarik & lepas file CSV di sini, atau klik untuk memilih").parentElement?.parentElement as HTMLElement;
    
    const file = new File(["corrupt data"], "image.png", { type: "image/png" });
    
    fireEvent.drop(dropzone, {
      dataTransfer: {
        files: [file],
      },
    });
    
    await waitFor(() => {
      expect(screen.getByText("Format file tidak didukung. Silakan gunakan file .csv")).toBeInTheDocument();
    });
  });

  it("handles successful CSV upload", async () => {
    window.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ message: "Berhasil mengimpor 1 task." }),
      } as any)
    );

    render(<ImportCsvModal isOpen={true} onClose={onClose} onSuccess={onSuccess} />);
    
    // 1. Select file
    const file = new File(["title,project_key\nTask 1,PRJ"], "tasks.csv", { type: "text/csv" });
    const input = document.querySelector("input[type='file']") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText("tasks.csv")).toBeInTheDocument();
    });

    // 2. Click upload button
    const submitBtn = screen.getByText("Mulai Impor");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText("Berhasil mengimpor 1 task.")).toBeInTheDocument();
      expect(onSuccess).toHaveBeenCalledTimes(1);
    });
  });

  it("handles CSV validation errors (422)", async () => {
    window.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: false,
        status: 422,
        json: () => Promise.resolve({
          detail: {
            errors: [
              { row: 2, field: "title", message: "Judul task wajib diisi." }
            ]
          }
        }),
      } as any)
    );

    render(<ImportCsvModal isOpen={true} onClose={onClose} onSuccess={onSuccess} />);
    
    const file = new File(["title,project_key\n,PRJ"], "tasks.csv", { type: "text/csv" });
    const input = document.querySelector("input[type='file']") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText("tasks.csv")).toBeInTheDocument();
    });

    const submitBtn = screen.getByText("Mulai Impor");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText("Baris 2")).toBeInTheDocument();
      expect(screen.getByText("title")).toBeInTheDocument();
      expect(screen.getByText("Judul task wajib diisi.")).toBeInTheDocument();
    });
  });

  it("handles CSV validation general error message (422 without detailed errors)", async () => {
    window.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: false,
        status: 422,
        json: () => Promise.resolve({
          detail: {
            message: "Format header tidak valid."
          }
        }),
      } as any)
    );

    render(<ImportCsvModal isOpen={true} onClose={onClose} onSuccess={onSuccess} />);
    
    const file = new File(["bad,headers"], "tasks.csv", { type: "text/csv" });
    const input = document.querySelector("input[type='file']") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText("tasks.csv")).toBeInTheDocument();
    });

    const submitBtn = screen.getByText("Mulai Impor");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText("Format header tidak valid.")).toBeInTheDocument();
    });
  });

  it("handles generic upload error", async () => {
    window.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: false,
        status: 400,
        json: () => Promise.resolve({ detail: "Gagal mengimpor CSV. Silakan periksa format file." }),
      } as any)
    );

    render(<ImportCsvModal isOpen={true} onClose={onClose} onSuccess={onSuccess} />);
    
    const file = new File(["title,project_key\nTask 1,PRJ"], "tasks.csv", { type: "text/csv" });
    const input = document.querySelector("input[type='file']") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText("tasks.csv")).toBeInTheDocument();
    });

    const submitBtn = screen.getByText("Mulai Impor");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText("Gagal mengimpor CSV. Silakan periksa format file.")).toBeInTheDocument();
    });
  });

  it("handles connection error during upload", async () => {
    window.fetch = vi.fn().mockImplementation(() =>
      Promise.reject(new Error("Network Error"))
    );

    render(<ImportCsvModal isOpen={true} onClose={onClose} onSuccess={onSuccess} />);
    
    const file = new File(["title,project_key\nTask 1,PRJ"], "tasks.csv", { type: "text/csv" });
    const input = document.querySelector("input[type='file']") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText("tasks.csv")).toBeInTheDocument();
    });

    const submitBtn = screen.getByText("Mulai Impor");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText("Terjadi kesalahan koneksi saat mengunggah file.")).toBeInTheDocument();
    });
  });
});
