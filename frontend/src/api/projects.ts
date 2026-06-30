import client from "./client";
import type { ProjectSummary } from "../types/meta";
import type { BoardResponse, TaskStatus } from "../types/task";

export const projectApi = {
  getSummary: (projectId: number) =>
    client
      .get<ProjectSummary>(`/api/v1/projects/${projectId}/summary`)
      .then((response) => response.data),

  getBoard: (
    projectId: number,
    params?: {
      limit?: number;
      status?: TaskStatus;
      before?: number;
      after?: number;
      start?: boolean;
      end?: boolean;
    },
  ) =>
    client
      .get<BoardResponse>(`/api/v1/projects/${projectId}/board`, { params })
      .then((response) => response.data),
};
