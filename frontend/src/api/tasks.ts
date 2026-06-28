import client from "./client";
import type {
  Task,
  TaskCreate,
  TaskUpdate,
  TaskListResponse,
} from "../types/task";

/** Query parameters accepted by GET /api/v1/tasks/ */
export interface ListTasksParams {
  page?: number;
  size?: number;
  status?: string;
  priority?: string;
  project_id?: number;
  sprint_id?: number;
  assignee_id?: number;
  team_id?: number;
  department_id?: number;
  quarter?: string;
  risk_level?: string;
  search?: string;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

export const taskApi = {
  /**
   * GET /api/v1/tasks/
   * Returns a paginated, filterable list of tasks.
   */
  getAll: (params?: ListTasksParams) =>
    client
      .get<TaskListResponse>("/api/v1/tasks/", { params })
      .then((r) => r.data),

  /**
   * GET /api/v1/tasks/{id}
   * Returns a single task by ID, or throws 404.
   */
  getById: (id: number) =>
    client.get<Task>(`/api/v1/tasks/${id}`).then((r) => r.data),

  /**
   * POST /api/v1/tasks/
   * Creates a new task with all required fields in the given project.
   */
  create: (data: TaskCreate, projectId: number) =>
    client.post<Task>(`/api/v1/tasks/?project_id=${projectId}`, data).then((r) => r.data),

  /**
   * PUT /api/v1/tasks/{id}
   * Partially updates a task (all fields optional).
   */
  update: (id: number, data: TaskUpdate) =>
    client.put<Task>(`/api/v1/tasks/${id}`, data).then((r) => r.data),

  /**
   * DELETE /api/v1/tasks/{id}
   * Deletes a task. Returns 204 No Content on success.
   */
  delete: (id: number) => client.delete(`/api/v1/tasks/${id}`),
};
