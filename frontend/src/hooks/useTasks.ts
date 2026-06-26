import { useState, useEffect, useCallback } from "react";
import { taskApi } from "../api/tasks";
import type { Task, TaskCreate, TaskUpdate } from "../types/task";

export function useTasks() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTasks = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await taskApi.getAll();
      setTasks(data);
    } catch {
      setError("Gagal memuat tasks. Pastikan backend berjalan.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const createTask = async (data: TaskCreate) => {
    const newTask = await taskApi.create(data);
    setTasks((prev) => [newTask, ...prev]); // optimistic-style prepend
    return newTask;
  };

  const updateTask = async (id: number, data: TaskUpdate) => {
    const updated = await taskApi.update(id, data);
    setTasks((prev) => prev.map((t) => (t.id === id ? updated : t)));
    return updated;
  };

  const deleteTask = async (id: number) => {
    // Optimistic delete
    setTasks((prev) => prev.filter((t) => t.id !== id));
    try {
      await taskApi.delete(id);
    } catch {
      // Rollback on failure
      fetchTasks();
      throw new Error("Gagal menghapus task.");
    }
  };

  return { tasks, loading, error, createTask, updateTask, deleteTask, refetch: fetchTasks };
}
