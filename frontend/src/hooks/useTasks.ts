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
  createTask: (data: TaskCreate, projectId: number) => Promise<Task>;
  updateTask: (id: number, data: TaskUpdate) => Promise<Task>;
  deleteTask: (id: number) => Promise<void>;
  refetch: () => void;
}

const DEFAULT_SIZE = 20;

export function useTasks(projectId: number | null = null): UseTasksResult {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [pagination, setPagination] = useState<
    Pick<TaskListResponse, "total" | "page" | "size" | "pages">
  >({ total: 0, page: 1, size: DEFAULT_SIZE, pages: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  // Reset page when projectId changes
  useEffect(() => {
    setPage(1);
  }, [projectId]);

  const fetchTasks = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await taskApi.getAll({ 
        page, 
        size: DEFAULT_SIZE,
        project_id: projectId || undefined 
      });
      
      setTasks(response.items);
      setPagination({
        total: response.total,
        page: response.page,
        size: response.size,
        pages: response.pages,
      });
    } catch {
      setError("Gagal memuat tasks. Pastikan Anda memiliki akses ke proyek ini.");
    } finally {
      setLoading(false);
    }
  }, [page, projectId]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  // Auto-clear error after 5 seconds
  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  const createTask = async (data: TaskCreate, pId: number): Promise<Task> => {
    setError(null);
    const newTask = await taskApi.create(data, pId);
    // Prepend to the list if it belongs to the current workspace
    if (!projectId || pId === projectId) {
      setTasks((prev) => [newTask, ...prev]);
    }
    return newTask;
  };

  const updateTask = async (id: number, data: TaskUpdate): Promise<Task> => {
    setError(null);
    const updated = await taskApi.update(id, data);
    setTasks((prev) => prev.map((t) => (t.id === id ? updated : t)));
    return updated;
  };

  const deleteTask = async (id: number): Promise<void> => {
    // Optimistic removal
    setTasks((prev) => prev.filter((t) => t.id !== id));
    try {
      setError(null);
      await taskApi.delete(id);
    } catch (err: any) {
      // Rollback on failure
      fetchTasks();
      const msg = err.response?.data?.detail || "Gagal menghapus task.";
      setError(msg);
      throw err;
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
