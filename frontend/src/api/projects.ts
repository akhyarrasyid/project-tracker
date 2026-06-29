import client from "./client";
import type { ProjectSummary } from "../types/meta";

export const projectApi = {
  getSummary: (projectId: number) =>
    client
      .get<ProjectSummary>(`/api/v1/projects/${projectId}/summary`)
      .then((response) => response.data),
};
