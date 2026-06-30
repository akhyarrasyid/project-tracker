import "@testing-library/jest-dom";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TaskTaskList } from "./TaskTaskList";

const tasks = [
  {
    id: 1,
    key: "PAY-1",
    title: "Handle duplicate callback",
    assignee: "Amanda",
    created_by: "admin",
    priority: "High",
    status: "In Progress",
    story_points: 5,
    due_date: "2026-07-05",
  },
  {
    id: 2,
    key: "PAY-2",
    title: "Add reconciliation export",
    assignee: "Bima",
    created_by: "owner",
    priority: "Low",
    status: "Todo",
    story_points: 2,
    due_date: "2026-07-01",
  },
] as any;

describe("TaskTaskList", () => {
  beforeEach(() => {
    Element.prototype.scrollIntoView = vi.fn();
  });

  it("renders the empty state when there are no tasks", () => {
    render(<TaskTaskList tasks={[]} onTaskClick={vi.fn()} />);

    expect(screen.getByText("Tidak ada issue yang cocok dengan filter aktif")).toBeInTheDocument();
  });

  it("sorts rows and opens items on click", () => {
    const onTaskClick = vi.fn();
    render(<TaskTaskList tasks={tasks} onTaskClick={onTaskClick} />);

    fireEvent.click(screen.getByText("Priority"));
    const issueButtons = screen.getAllByRole("button");
    const payOne = issueButtons.find((button) => button.textContent === "PAY-1");
    expect(payOne).toBeDefined();
    payOne?.click();

    expect(onTaskClick).toHaveBeenCalledWith(tasks[0]);
    expect(screen.getByText("Total: 2 issues")).toBeInTheDocument();
  });

  it("supports keyboard navigation and Enter to open the selected issue", () => {
    const onTaskClick = vi.fn();
    render(<TaskTaskList tasks={tasks} onTaskClick={onTaskClick} />);

    const container = screen.getByRole("table").parentElement as HTMLDivElement;
    fireEvent.keyDown(container, { key: "ArrowDown" });
    fireEvent.keyDown(container, { key: "Enter" });

    expect(onTaskClick).toHaveBeenCalledWith(tasks[0]);
  });
});
