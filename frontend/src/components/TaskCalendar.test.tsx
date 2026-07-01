import "@testing-library/jest-dom";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TaskCalendar } from "./TaskCalendar";

const tasks = [
  {
    id: 1,
    key: "PAY-1",
    title: "Handle duplicate callback",
    priority: "High",
    due_date: "2026-06-15",
  },
  {
    id: 2,
    key: "PAY-2",
    title: "Export reconciliation report",
    priority: "Low",
    due_date: "2026-07-04",
  },
] as any;

describe("TaskCalendar", () => {
  it("renders the default month and opens issues from the day grid", () => {
    const onTaskClick = vi.fn();
    render(<TaskCalendar tasks={tasks} onTaskClick={onTaskClick} />);

    expect(screen.getByText(/Juni 2026/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /PAY-1: Handle duplicate callback/i }));
    expect(onTaskClick).toHaveBeenCalledWith(tasks[0]);
  });

  it("navigates between months and can jump back to the default month", () => {
    render(<TaskCalendar tasks={tasks} onTaskClick={vi.fn()} />);

    const buttons = screen.getAllByRole("button");
    fireEvent.click(buttons[2]);
    expect(screen.getByText(/Juli 2026/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /PAY-2: Export reconciliation report/i })).toBeInTheDocument();

    fireEvent.click(buttons[0]);
    expect(screen.getByText(/Juni 2026/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Hari Ini/i }));
    expect(screen.getByText(/Juni 2026/i)).toBeInTheDocument();
  });
});
