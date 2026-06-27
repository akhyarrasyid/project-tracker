import { useTasks } from "./hooks/useTasks";
import { KanbanColumn } from "./components/KanbanColumn";
import { CreateTaskForm } from "./components/CreateTaskForm";
import type { TaskStatus } from "./types/task";

const STATUSES: TaskStatus[] = ["Todo", "In Progress", "Review", "Blocked", "Done"];

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

  const tasksByStatus = (status: TaskStatus) =>
    tasks.filter((t) => t.status === status);

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-100 shadow-sm sticky top-0 z-10">
        <div className="max-w-screen-xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
            <div>
              <h1 className="text-lg font-bold text-slate-800">TaskBoard</h1>
              <p className="text-xs text-slate-400 hidden sm:block">Project Tracker — Enterprise</p>
            </div>
          </div>
          <div className="flex items-center gap-4 text-sm text-slate-400">
            <span>
              <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block mr-1" />
              {pagination.total} tasks
            </span>
            <span>Page {pagination.page}/{pagination.pages || 1}</span>
          </div>
        </div>
      </header>

      {/* Main board */}
      <main className="max-w-screen-xl mx-auto px-4 py-6">
        {/* Error banner */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm flex items-center gap-2">
            <svg className="w-4 h-4 shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            {error}
          </div>
        )}

        {/* Loading skeleton */}
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            {[0, 1, 2, 3, 4].map((i) => (
              <div key={i} className="space-y-3">
                <div className="h-5 bg-slate-200 rounded-full w-24 animate-pulse" />
                {[0, 1, 2].map((j) => (
                  <div key={j} className="bg-white rounded-xl border-2 border-slate-100 p-4 space-y-2 animate-pulse">
                    <div className="h-3 bg-slate-200 rounded w-16" />
                    <div className="h-4 bg-slate-200 rounded w-full" />
                    <div className="h-3 bg-slate-100 rounded w-3/4" />
                  </div>
                ))}
              </div>
            ))}
          </div>
        ) : (
          <>
            {/* Kanban board — 5 columns */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
              {STATUSES.map((status) => (
                <KanbanColumn
                  key={status}
                  status={status}
                  tasks={tasksByStatus(status)}
                  onUpdate={updateTask}
                  onDelete={deleteTask}
                  extra={
                    status === "Todo" ? (
                      <CreateTaskForm onCreate={createTask} />
                    ) : undefined
                  }
                />
              ))}
            </div>

            {/* Pagination */}
            {pagination.pages > 1 && (
              <div className="mt-8 flex items-center justify-center gap-2">
                <button
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page <= 1}
                  className="px-3 py-1.5 text-sm border border-slate-200 rounded-lg hover:bg-slate-100 disabled:opacity-40 transition-colors"
                >
                  ← Prev
                </button>
                <span className="text-sm text-slate-500">
                  Page {pagination.page} of {pagination.pages}
                </span>
                <button
                  onClick={() => setPage(Math.min(pagination.pages, page + 1))}
                  disabled={page >= pagination.pages}
                  className="px-3 py-1.5 text-sm border border-slate-200 rounded-lg hover:bg-slate-100 disabled:opacity-40 transition-colors"
                >
                  Next →
                </button>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
