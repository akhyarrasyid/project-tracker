import {
  closestCenter,
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import type { DragEndEvent } from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useMutation } from "@tanstack/react-query";
import { useMemo, useRef, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import { queryClient } from "../app/query-client";
import { issueApi } from "../api/issues";
import { taskApi } from "../api/tasks";
import { KanbanColumn } from "../components/KanbanColumn";
import { CreateTaskForm, type CreateTaskFormHandle } from "../components/CreateTaskForm";
import { TaskCard } from "../components/TaskCard";
import { applyOptimisticMove } from "../features/issues/board-cache";
import { IssueDetailPanel } from "../features/issues/components/IssueDetailPanel";
import { useBoardQuery } from "../features/issues/hooks/useBoardQuery";
import type { BoardResponse, IssueMoveInput, Task, TaskCreate, TaskStatus } from "../types/task";

const COLUMNS: TaskStatus[] = ["Todo", "In Progress", "Review", "Done"];

function findTask(board: BoardResponse, taskId: number) {
  for (const status of COLUMNS) {
    const task = board.columns[status].items.find((item) => item.id === taskId);
    if (task) {
      return task;
    }
  }
  return null;
}

function buildMoveInput(board: BoardResponse, activeTaskId: number, overId: string): IssueMoveInput | null {
  if (overId.startsWith("column:")) {
    const status = overId.replace("column:", "") as TaskStatus;
    const items = board.columns[status].items.filter((item) => item.id !== activeTaskId);
    const last = items.at(-1);
    return {
      status,
      after_issue_id: last?.id ?? null,
    };
  }

  if (!overId.startsWith("task:")) {
    return null;
  }

  const overTaskId = Number(overId.replace("task:", ""));
  const overTask = findTask(board, overTaskId);
  if (!overTask) {
    return null;
  }

  const status = overTask.status;
  const items = board.columns[status].items.filter((item) => item.id !== activeTaskId);
  const overIndex = items.findIndex((item) => item.id === overTaskId);
  const previous = overIndex > 0 ? items[overIndex - 1] : null;

  return {
    status,
    before_issue_id: overTask.id,
    after_issue_id: previous?.id ?? null,
  };
}

function SortableTaskCard({
  task,
  onTaskClick,
}: {
  task: Task;
  onTaskClick: (task: Task) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({
      id: `task:${task.id}`,
      data: { type: "task", status: task.status, taskId: task.id },
    });

  return (
    <div
      ref={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
      }}
      {...attributes}
      {...listeners}
    >
      <TaskCard task={task} onTaskClick={onTaskClick} />
    </div>
  );
}

export function ProjectBoardPage() {
  const { projectKey } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const boardQuery = useBoardQuery(projectKey);
  const [activeTaskId, setActiveTaskId] = useState<number | null>(null);
  const quickAddRefs = useRef<Partial<Record<TaskStatus, CreateTaskFormHandle | null>>>({});
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const totalIssues = useMemo(
    () =>
      COLUMNS.reduce(
        (sum, status) => sum + (boardQuery.data?.columns[status].total_count ?? 0),
        0,
      ),
    [boardQuery.data],
  );

  async function handleCreateTask(payload: TaskCreate, projectId: number) {
    const created = await taskApi.create(payload, projectId);
    await queryClient.invalidateQueries({ queryKey: ["board", projectKey] });
    await queryClient.invalidateQueries({ queryKey: ["my-issues"] });
    return created;
  }

  const moveMutation = useMutation({
    mutationFn: ({ issueId, input }: { issueId: number; input: IssueMoveInput }) =>
      issueApi.move(issueId, input),
    onMutate: async ({ issueId, input }) => {
      await queryClient.cancelQueries({ queryKey: ["board", projectKey] });
      const previousBoard = queryClient.getQueryData<BoardResponse>(["board", projectKey]);
      if (previousBoard) {
        const task = findTask(previousBoard, issueId);
        if (task) {
          queryClient.setQueryData(["board", projectKey], applyOptimisticMove(previousBoard, task, input));
        }
      }
      return { previousBoard };
    },
    onError: (_error, _variables, context) => {
      if (context?.previousBoard) {
        queryClient.setQueryData(["board", projectKey], context.previousBoard);
      }
    },
    onSuccess: (task) => {
      queryClient.setQueryData(["issue", task.key], task);
    },
    onSettled: async () => {
      await queryClient.invalidateQueries({ queryKey: ["board", projectKey] });
      await queryClient.invalidateQueries({ queryKey: ["my-issues"] });
    },
  });

  function handleDragEnd(event: DragEndEvent) {
    setActiveTaskId(null);
    const activeId = String(event.active.id);
    const overId = event.over ? String(event.over.id) : null;
    if (!boardQuery.data || !overId || !activeId.startsWith("task:")) {
      return;
    }

    const issueId = Number(activeId.replace("task:", ""));
    const moveInput = buildMoveInput(boardQuery.data, issueId, overId);
    if (!moveInput) {
      return;
    }
    const movingTask = findTask(boardQuery.data, issueId);
    if (!movingTask) {
      return;
    }

    moveMutation.mutate({
      issueId,
      input: {
        ...moveInput,
        expected_version: movingTask.version,
      },
    });
  }

  const activeTask =
    activeTaskId && boardQuery.data ? findTask(boardQuery.data, activeTaskId) : null;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs font-medium tracking-[0.18em] text-[color:var(--app-text-soft)]">Board view</div>
          <h2 className="app-heading mt-1 text-2xl font-semibold">Current work</h2>
        </div>
        <div className="rounded-full border border-[color:var(--app-border)] bg-[color:var(--app-panel)] px-3 py-1.5 text-sm text-[color:var(--app-text-soft)]">
          {totalIssues} issues
        </div>
      </div>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={(event) => setActiveTaskId(Number(String(event.active.id).replace("task:", "")))}
        onDragEnd={handleDragEnd}
      >
        <div className="app-scrollbar overflow-x-auto pb-2">
          <div className="flex min-w-max gap-5">
            {COLUMNS.map((column) => {
              const boardColumn = boardQuery.data?.columns[column];
              const tasks = boardColumn?.items ?? [];

              return (
                <SortableContext
                  key={column}
                  items={tasks.map((task) => `task:${task.id}`)}
                  strategy={verticalListSortingStrategy}
                >
                  <KanbanColumn
                    status={column}
                    tasks={tasks}
                    totalCount={boardColumn?.total_count ?? 0}
                    onAddIssue={() => quickAddRefs.current[column]?.open()}
                    renderTask={(task) => (
                      <SortableTaskCard
                        key={task.id}
                        task={task}
                        onTaskClick={(item) => {
                          const nextParams = new URLSearchParams(searchParams);
                          nextParams.set("issue", item.key);
                          setSearchParams(nextParams);
                        }}
                      />
                    )}
                    extra={
                      <CreateTaskForm
                        ref={(handle) => {
                          quickAddRefs.current[column] = handle;
                        }}
                        onCreate={handleCreateTask}
                        currentProjectId={boardQuery.projectQuery.data?.id}
                        initialStatus={column}
                      />
                    }
                  />
                </SortableContext>
              );
            })}
          </div>
        </div>

        <DragOverlay>
          {activeTask ? (
            <div className="w-[320px] rotate-[1deg] opacity-95">
              <TaskCard task={activeTask} onTaskClick={() => {}} />
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>

      <IssueDetailPanel
        issueKey={searchParams.get("issue") ?? undefined}
        mode="sheet"
        onClose={() => {
          const nextParams = new URLSearchParams(searchParams);
          nextParams.delete("issue");
          setSearchParams(nextParams);
        }}
      />
    </div>
  );
}
