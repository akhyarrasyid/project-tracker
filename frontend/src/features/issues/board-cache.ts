import type { BoardResponse, IssueMoveInput, Task, TaskStatus } from "../../types/task";

const STATUSES: TaskStatus[] = ["Todo", "In Progress", "Review", "Done"];

function cloneColumn(column: BoardResponse["columns"][TaskStatus]) {
  return {
    ...column,
    items: [...column.items],
  };
}

export function removeTaskFromBoard(board: BoardResponse, taskId: number) {
  const columns = {} as BoardResponse["columns"];

  for (const status of STATUSES) {
    const column = cloneColumn(board.columns[status]);
    const nextItems = column.items.filter((item) => item.id !== taskId);
    columns[status] = {
      ...column,
      items: nextItems,
      total_count: column.total_count - (column.items.length - nextItems.length),
    };
  }

  return { columns };
}

export function applyOptimisticMove(
  board: BoardResponse,
  task: Task,
  move: IssueMoveInput,
) {
  const withoutTask = removeTaskFromBoard(board, task.id);
  const destination = cloneColumn(withoutTask.columns[move.status]);
  const movedTask: Task = { ...task, status: move.status };

  let insertAt = destination.items.length;
  if (move.before_issue_id != null) {
    const beforeIndex = destination.items.findIndex((item) => item.id === move.before_issue_id);
    if (beforeIndex >= 0) {
      insertAt = beforeIndex;
    }
  } else if (move.after_issue_id != null) {
    const afterIndex = destination.items.findIndex((item) => item.id === move.after_issue_id);
    if (afterIndex >= 0) {
      insertAt = afterIndex + 1;
    }
  }

  destination.items.splice(insertAt, 0, movedTask);
  destination.total_count += 1;

  return {
    columns: {
      ...withoutTask.columns,
      [move.status]: destination,
    },
  } satisfies BoardResponse;
}
