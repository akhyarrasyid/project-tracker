import { useState, useEffect, useCallback } from "react";
import { taskApi } from "../api/tasks";
import type { Task, TaskCreate, TaskUpdate, TaskListResponse } from "../types/task";

/** State returned by useTasks */
export interface UseTasksResult {
  tasks: Task[];
  pagination: Pick<TaskListResponse, "total" | "page" | "size" | "pages">;
  loading: boolean;
  error: string | null;
  page: number;
  setPage: (page: number) => void;
  createTask: (data: TaskCreate) => Promise<Task>;
  updateTask: (id: number, data: TaskUpdate) => Promise<Task>;
  deleteTask: (id: number) => Promise<void>;
  refetch: () => void;
}

const DEFAULT_SIZE = 20;

export function useTasks(): UseTasksResult {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [pagination, setPagination] = useState<
    Pick<TaskListResponse, "total" | "page" | "size" | "pages">
  >({ total: 0, page: 1, size: DEFAULT_SIZE, pages: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  const fetchTasks = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await taskApi.getAll({ page, size: DEFAULT_SIZE });
      setTasks(response.items);
      setPagination({
        total: response.total,
        page: response.page,
        size: response.size,
        pages: response.pages,
      });
    } catch {
      setError("Gagal memuat tasks. Pastikan backend berjalan.");
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const createTask = async (data: TaskCreate): Promise<Task> => {
    const newTask = await taskApi.create(data);
    // Prepend to the list (optimistic); a refetch keeps pagination accurate
    setTasks((prev) => [newTask, ...prev]);
    return newTask;
  };

  const updateTask = async (id: number, data: TaskUpdate): Promise<Task> => {
    const updated = await taskApi.update(id, data);
    setTasks((prev) => prev.map((t) => (t.id === id ? updated : t)));
    return updated;
  };

  const deleteTask = async (id: number): Promise<void> => {
    // Optimistic removal
    setTasks((prev) => prev.filter((t) => t.id !== id));
    try {
      await taskApi.delete(id);
    } catch {
      // Rollback on failure
      fetchTasks();
      throw new Error("Gagal menghapus task.");
    }
  };

  return {
    tasks,
    pagination,
    loading,
    error,
    page,
    setPage,
    createTask,
    updateTask,
    deleteTask,
    refetch: fetchTasks,
  };
}
