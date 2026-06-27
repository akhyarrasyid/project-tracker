import axios from "axios";
import type {
  Task,
  TaskCreate,
  TaskUpdate,
  TaskListResponse,
} from "../types/task";

/**
 * Axios instance bound to the backend base URL.
 * In development, Vite's proxy rewrites `/api/v1/**` to `http://localhost:8000/api/v1/**`.
 * In Docker, nginx proxies `/api/` to the backend container.
 */
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
});

/** Query parameters accepted by GET /api/v1/tasks/ */
export interface ListTasksParams {
  page?: number;
  size?: number;
  status?: string;
  priority?: string;
  department?: string;
  assignee?: string;
  team?: string;
  sprint?: string;
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
    api
      .get<TaskListResponse>("/api/v1/tasks/", { params })
      .then((r) => r.data),

  /**
   * GET /api/v1/tasks/{id}
   * Returns a single task by ID, or throws 404.
   */
  getById: (id: number) =>
    api.get<Task>(`/api/v1/tasks/${id}`).then((r) => r.data),

  /**
   * POST /api/v1/tasks/
   * Creates a new task with all required fields.
   */
  create: (data: TaskCreate) =>
    api.post<Task>("/api/v1/tasks/", data).then((r) => r.data),

  /**
   * PUT /api/v1/tasks/{id}
   * Partially updates a task (all fields optional).
   */
  update: (id: number, data: TaskUpdate) =>
    api.put<Task>(`/api/v1/tasks/${id}`, data).then((r) => r.data),

  /**
   * DELETE /api/v1/tasks/{id}
   * Deletes a task. Returns 204 No Content on success.
   */
  delete: (id: number) => api.delete(`/api/v1/tasks/${id}`),
};
