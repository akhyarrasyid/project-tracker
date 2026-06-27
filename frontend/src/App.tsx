import { useState } from "react";
import { useTasks } from "./hooks/useTasks";
import { KanbanColumn } from "./components/KanbanColumn";
import { CreateTaskForm } from "./components/CreateTaskForm";
import { TaskDetailModal } from "./components/TaskDetailModal";
import { TaskCalendar } from "./components/TaskCalendar";
import { TaskTaskList } from "./components/TaskTaskList";
import type { Task } from "./types/task";

const COLUMNS = ["Todo", "In Progress", "Review", "Done"];

export default function App() {
  const {
    tasks,
    pagination,
    loading,
    error,
    page,
    setPage,
    createTask,
    updateTask,
    deleteTask,
  } = useTasks();

  const [activeTab, setActiveTab] = useState<"board" | "list" | "calendar">("board");
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);

  // Group tasks by column
  const getTasksForColumn = (col: string) => {
    if (col === "In Progress") {
      // In Progress column displays In Progress AND Blocked tasks
      return tasks.filter((t) => t.status === "In Progress" || t.status === "Blocked");
    }
    if (col === "Review") {
      return tasks.filter((t) => t.status === "Review");
    }
    return tasks.filter((t) => t.status === col);
  };

  // Calculate overall progress percentage
  const calculateDonePercentage = () => {
    if (pagination.total === 0) return 0;
    const doneTasks = tasks.filter((t) => t.status === "Done");
    // Just a representation from the loaded tasks list or approximate
    return Math.round((doneTasks.length / tasks.length) * 100) || 0;
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      {/* Top Centered Header Navigation */}
      <header className="bg-white border-b border-slate-100 shadow-sm sticky top-0 z-10">
        <div className="max-w-screen-xl mx-auto px-6 h-16 flex items-center justify-between">
          {/* Logo / Title */}
          <div className="flex items-center gap-3 w-1/4">
            <div className="w-9 h-9 bg-blue-600 rounded-lg flex items-center justify-center shadow-sm shadow-blue-500/25">
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
            <div>
              <h1 className="text-md font-bold text-slate-800 tracking-tight leading-none mb-0.5">TaskBoard</h1>
              <span className="text-[10px] font-semibold text-slate-400">What The Dog Doin'</span>
            </div>
          </div>

          {/* Centered Navigation Tabs */}
          <nav className="flex items-center justify-center gap-6 h-full">
            {(["board", "list", "calendar"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`h-full px-3 text-sm font-semibold capitalize relative transition-all duration-200 cursor-pointer ${
                  activeTab === tab
                    ? "text-blue-600 font-bold"
                    : "text-slate-500 hover:text-slate-800"
                }`}
              >
                {tab}
                {activeTab === tab && (
                  <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600 rounded-full" />
                )}
              </button>
            ))}
          </nav>

          {/* Status info & Pagination controls */}
          <div className="flex items-center justify-end gap-4 w-1/4 text-sm text-slate-500">
            <span className="text-xs bg-slate-100 px-2.5 py-1 rounded-full font-bold text-slate-600 hidden md:inline-block">
              ⚡ Progress: {calculateDonePercentage()}%
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page <= 1}
                className="p-1 rounded border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-40 transition-colors"
                title="Halaman Sebelumnya"
              >
                <svg className="w-4 h-4 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <span className="text-xs font-semibold whitespace-nowrap">
                {page} / {pagination.pages || 1}
              </span>
              <button
                onClick={() => setPage(Math.min(pagination.pages, page + 1))}
                disabled={page >= pagination.pages}
                className="p-1 rounded border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-40 transition-colors"
                title="Halaman Selanjutnya"
              >
                <svg className="w-4 h-4 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-screen-xl w-full mx-auto px-6 py-6 flex flex-col gap-6">
        {/* Error Notification */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm flex items-center gap-2 shadow-sm">
            <svg className="w-4 h-4 shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <span>{error}</span>
          </div>
        )}

        {/* Loading Spinner / Skeleton */}
        {loading ? (
          <div className="flex-1 flex items-center justify-center py-24">
            <div className="flex flex-col items-center gap-3">
              <div className="w-12 h-12 border-4 border-blue-600/20 border-t-blue-600 rounded-full animate-spin" />
              <span className="text-sm font-semibold text-slate-500">Memuat data task...</span>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col">
            {/* Board View */}
            {activeTab === "board" && (
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 flex-1">
                {COLUMNS.map((col) => (
                  <KanbanColumn
                    key={col}
                    status={col}
                    tasks={getTasksForColumn(col)}
                    onUpdate={updateTask}
                    onDelete={deleteTask}
                    onTaskClick={setSelectedTask}
                    extra={
                      col === "Todo" ? (
                        <CreateTaskForm onCreate={createTask} />
                      ) : undefined
                    }
                  />
                ))}
              </div>
            )}

            {/* List View */}
            {activeTab === "list" && (
              <TaskTaskList tasks={tasks} onTaskClick={setSelectedTask} />
            )}

            {/* Calendar View */}
            {activeTab === "calendar" && (
              <TaskCalendar tasks={tasks} onTaskClick={setSelectedTask} />
            )}
          </div>
        )}
      </main>

      {/* Task Details Modal */}
      {selectedTask && (
        <TaskDetailModal
          task={selectedTask}
          onUpdate={updateTask}
          onDelete={deleteTask}
          onClose={() => setSelectedTask(null)}
        />
      )}
    </div>
  );
}
