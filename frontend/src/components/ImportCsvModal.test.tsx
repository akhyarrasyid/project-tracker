import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ImportCsvModal } from "./ImportCsvModal";
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
    
    // Should trigger fetch on template endpoint
    expect(window.fetch).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/tasks/import-template",
      expect.any(Object)
    );
  });
});
