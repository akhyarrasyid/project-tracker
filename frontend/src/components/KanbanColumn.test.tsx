import "@testing-library/jest-dom";
import { DndContext } from "@dnd-kit/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { KanbanColumn } from "./KanbanColumn";

describe("KanbanColumn", () => {
  it("calls the quick add handler from the column header plus button", () => {
    const onAddIssue = vi.fn();

    render(
      <DndContext>
        <KanbanColumn
          status="In Progress"
          tasks={[]}
          totalCount={0}
          renderTask={() => null}
          onAddIssue={onAddIssue}
        />
      </DndContext>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Add issue to In progress" }));

    expect(onAddIssue).toHaveBeenCalledTimes(1);
  });
});
