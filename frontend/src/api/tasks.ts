import axios from "axios";
import type { Task, TaskCreate, TaskUpdate } from "../types/task";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
});

export const taskApi = {
  getAll: () => api.get<Task[]>("/tasks/").then((r) => r.data),

  create: (data: TaskCreate) =>
    api.post<Task>("/tasks/", data).then((r) => r.data),

  update: (id: number, data: TaskUpdate) =>
    api.put<Task>(`/tasks/${id}`, data).then((r) => r.data),

  delete: (id: number) => api.delete(`/tasks/${id}`),
};
