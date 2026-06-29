import client from "./client";
import type {
  IssueActivity,
  IssueComment,
  IssueMoveInput,
  IssuePatchInput,
  Task,
  TaskUpdate,
} from "../types/task";

export const issueApi = {
  getByKey: (issueKey: string) =>
    client.get<Task>(`/api/v1/issues/${issueKey}`).then((response) => response.data),

  update: (issueKey: string, data: TaskUpdate) =>
    client.put<Task>(`/api/v1/issues/${issueKey}`, data).then((response) => response.data),

  patch: (issueId: number, data: IssuePatchInput) =>
    client.patch<Task>(`/api/v1/issues/${issueId}`, data).then((response) => response.data),

  move: (issueId: number, data: IssueMoveInput) =>
    client.patch<Task>(`/api/v1/issues/${issueId}/move`, data).then((response) => response.data),

  getComments: (issueId: number) =>
    client.get<IssueComment[]>(`/api/v1/issues/${issueId}/comments`).then((response) => response.data),

  createComment: (issueId: number, content: string, parentId?: number | null) =>
    client
      .post<IssueComment>(`/api/v1/issues/${issueId}/comments`, {
        content,
        parent_id: parentId ?? null,
      })
      .then((response) => response.data),

  getActivities: (issueId: number) =>
    client
      .get<IssueActivity[]>(`/api/v1/issues/${issueId}/activities`)
      .then((response) => response.data),

  deleteById: (issueId: number) => client.delete(`/api/v1/issues/${issueId}`),

  delete: (issueKey: string) => client.delete(`/api/v1/issues/${issueKey}`),
};
