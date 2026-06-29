import client from "./client";
import type { IssueMoveInput, Task, TaskUpdate } from "../types/task";

export const issueApi = {
  getByKey: (issueKey: string) =>
    client.get<Task>(`/api/v1/issues/${issueKey}`).then((response) => response.data),

  update: (issueKey: string, data: TaskUpdate) =>
    client.put<Task>(`/api/v1/issues/${issueKey}`, data).then((response) => response.data),

  move: (issueId: number, data: IssueMoveInput) =>
    client.patch<Task>(`/api/v1/issues/${issueId}/move`, data).then((response) => response.data),

  delete: (issueKey: string) => client.delete(`/api/v1/issues/${issueKey}`),
};
