import { useState, useEffect } from "react";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { useTasks } from "./hooks/useTasks";
import { KanbanColumn } from "./components/KanbanColumn";
import { CreateTaskForm } from "./components/CreateTaskForm";
import { TaskDetailModal } from "./components/TaskDetailModal";
import { TaskCalendar } from "./components/TaskCalendar";
import { TaskTaskList } from "./components/TaskTaskList";
import { LoginPage } from "./components/LoginPage";
import { ProjectSidebar } from "./components/ProjectSidebar";
import { Dashboard } from "./components/Dashboard";
import { ImportCsvModal } from "./components/ImportCsvModal";
import { metaApi } from "./api/meta";
import type { Task } from "./types/task";
import type { ProjectMeta } from "./types/meta";

const COLUMNS = ["Todo", "In Progress", "Review", "Done"];

function AppContent() {
  const { user, loading: authLoading } = useAuth();
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(1);
  const [projects, setProjects] = useState<ProjectMeta[]>([]);
  const [activeTab, setActiveTab] = useState<"board" | "list" | "calendar">("board");
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);

  // Hook handles project filtering, task operations, and pagination automatically
  const {
    tasks,
    pagination,
    loading: tasksLoading,
    error,
    page,
    setPage,
    createTask,
    updateTask,
    deleteTask,
    refetch,
  } = useTasks(selectedProjectId);

  // Fetch projects list when user logs in
  useEffect(() => {
    if (user) {
      metaApi.getProjects()
        .then(setProjects)
        .catch(console.error);
    } else {
      setProjects([]);
      setSelectedProjectId(null);
    }
  }, [user]);

  // Find currently active project details
  const activeProject = projects.find((p) => p.id === selectedProjectId);

  // Group tasks by column
  const getTasksForColumn = (col: string) => {
    if (col === "In Progress") {
      return tasks.filter((t) => t.status === "In Progress" || t.status === "Blocked");
    }
    if (col === "Review") {
      return tasks.filter((t) => t.status === "Review");
    }
    return tasks.filter((t) => t.status === col);
  };

  // Calculate overall progress percentage
  const calculateDonePercentage = () => {
    if (tasks.length === 0) return 0;
    const doneTasks = tasks.filter((t) => t.status === "Done");
    return Math.round((doneTasks.length / tasks.length) * 100);
  };

  if (authLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center font-sans">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-blue-600/20 border-t-blue-600 rounded-full animate-spin" />
          <span className="text-xs font-semibold text-slate-500">Menghubungkan ke server...</span>
        </div>
      </div>
    );
  }

  if (!user) {
    return <LoginPage />;
  }

  return (
    <div className="min-h-screen bg-slate-50 flex font-sans">
      {/* Sidebar Navigation */}
      <ProjectSidebar
        selectedProjectId={selectedProjectId}
        onSelectProject={(id) => {
          setSelectedProjectId(id);
          refetch();
        }}
      />

      {/* Main Workspace Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {selectedProjectId === null ? (
          // Dashboard Landing View
          <div className="p-8 overflow-y-auto flex-1">
            <Dashboard
              onSelectProject={(id) => setSelectedProjectId(id)}
              onTaskClick={setSelectedTask}
            />
          </div>
        ) : (
          // Project Workspace View
          <>
            {/* Header */}
            <header className="bg-white border-b border-slate-100 shadow-sm sticky top-0 z-10">
              <div className="px-8 h-16 flex items-center justify-between">
                {/* Project Title Info */}
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                    Proyek /
                  </span>
                  <h2 className="text-sm font-bold text-slate-800 truncate">
                    {activeProject ? activeProject.name : `Proyek ID: ${selectedProjectId}`}
                  </h2>
                  {activeProject && (
                    <span className="text-[10px] font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full shrink-0">
                      {activeProject.key}
                    </span>
                  )}
                  <button
                    onClick={() => setIsImportModalOpen(true)}
                    className="ml-3 inline-flex items-center gap-1.5 text-[10px] font-bold text-slate-500 hover:text-blue-600 bg-slate-100 hover:bg-blue-50 px-2.5 py-1 rounded-full transition-all duration-200 cursor-pointer"
                  >
                    <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                    </svg>
                    Impor CSV
                  </button>
                </div>

                {/* Centered Tabs */}
                <nav className="flex items-center justify-center gap-6 h-full ml-4">
                  {(["board", "list", "calendar"] as const).map((tab) => (
                    <button
                      key={tab}
                      onClick={() => setActiveTab(tab)}
                      className={`h-full px-3 text-xs font-bold uppercase tracking-wider relative transition-all duration-200 cursor-pointer ${
                        activeTab === tab
                          ? "text-blue-600"
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

                {/* Progress bar + Pagination */}
                <div className="flex items-center justify-end gap-5 text-sm text-slate-500">
                  <span className="text-[10px] bg-slate-100 px-2.5 py-1 rounded-full font-bold text-slate-600 hidden md:inline-block">
                    ⚡ Progress: {calculateDonePercentage()}%
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setPage(Math.max(1, page - 1))}
                      disabled={page <= 1}
                      className="p-1 rounded border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-40 transition-colors cursor-pointer"
                      title="Halaman Sebelumnya"
                    >
                      <svg className="w-3.5 h-3.5 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                      </svg>
                    </button>
                    <span className="text-[11px] font-bold whitespace-nowrap">
                      {page} / {pagination.pages || 1}
                    </span>
                    <button
                      onClick={() => setPage(Math.min(pagination.pages, page + 1))}
                      disabled={page >= pagination.pages}
                      className="p-1 rounded border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-40 transition-colors cursor-pointer"
                      title="Halaman Selanjutnya"
                    >
                      <svg className="w-3.5 h-3.5 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </header>

            {/* Content Body */}
            <main className="flex-1 p-8 overflow-y-auto flex flex-col gap-6">
              {/* Error Notice */}
              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-xs font-semibold flex items-center gap-2 shadow-sm">
                  <svg className="w-4 h-4 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                  <span>{error}</span>
                </div>
              )}

              {tasksLoading ? (
                <div className="flex-1 flex items-center justify-center py-24">
                  <div className="flex flex-col items-center gap-2">
                    <div className="w-8 h-8 border-3 border-blue-600/20 border-t-blue-600 rounded-full animate-spin" />
                    <span className="text-xs font-semibold text-slate-500">Memuat data task...</span>
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
                              <CreateTaskForm onCreate={createTask} currentProjectId={selectedProjectId} />
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
          </>
        )}
      </div>

      {/* Task Details Modal */}
      {selectedTask && (
        <TaskDetailModal
          task={selectedTask}
          onUpdate={updateTask}
          onDelete={deleteTask}
          onClose={() => setSelectedTask(null)}
        />
      )}

      {/* CSV Import Modal */}
      <ImportCsvModal
        isOpen={isImportModalOpen}
        onClose={() => setIsImportModalOpen(false)}
        onSuccess={refetch}
      />
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
