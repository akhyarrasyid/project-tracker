import React from "react";
import { useAuth } from "../contexts/useAuth";
import type { Task } from "../types/task";
import { useMyIssuesQuery } from "../features/issues/hooks/useMyIssuesQuery";
import { useProjectsQuery } from "../features/projects/hooks/useProjectsQuery";

interface DashboardProps {
  onSelectProject: (projectId: number) => void;
  onTaskClick: (task: Task) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ onSelectProject, onTaskClick }) => {
  const { user } = useAuth();
  const projectsQuery = useProjectsQuery();
  const myIssuesQuery = useMyIssuesQuery(user?.id);
  const projects = projectsQuery.data ?? [];
  const myTasks = myIssuesQuery.data?.items ?? [];
  const loadingProjects = projectsQuery.isLoading;
  const loadingTasks = myIssuesQuery.isLoading;

  const PRIORITY_COLORS: Record<string, string> = {
    Low: "bg-slate-50 text-slate-600 border-slate-200/60",
    Medium: "bg-blue-50 text-blue-600 border-blue-100",
    High: "bg-orange-50 text-orange-600 border-orange-100",
    Critical: "bg-red-50 text-red-600 border-red-100",
  };

  const STATUS_BADGES: Record<string, string> = {
    Todo: "bg-slate-100 text-slate-700",
    "In Progress": "bg-blue-100 text-blue-800",
    Review: "bg-purple-100 text-purple-800",
    Blocked: "bg-red-100 text-red-800",
    Done: "bg-green-100 text-green-800",
  };

  return (
    <div className="flex-1 flex flex-col gap-8 max-w-screen-xl w-full mx-auto animate-fade-in">
      {/* Header section */}
      <div className="flex flex-col gap-1.5 border-b border-slate-100 pb-6">
        <h2 className="text-2xl font-bold text-slate-800 tracking-tight">
          Selamat datang kembali, {user?.full_name}!
        </h2>
        <p className="text-sm text-slate-500">
          Berikut adalah ringkasan pekerjaan dan proyek Anda untuk hari ini.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: My Tasks (Takes 2 cols) */}
        <div className="lg:col-span-2 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h3 className="text-md font-bold text-slate-800 flex items-center gap-2">
              <span className="w-1.5 h-6 bg-blue-600 rounded-full" />
              Tugas Saya
            </h3>
            <span className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full font-bold">
              {myTasks.length} Aktif
            </span>
          </div>

          <div className="bg-white rounded-xl border border-slate-150 shadow-sm overflow-hidden min-h-[200px] flex flex-col justify-between">
            {loadingTasks ? (
              <div className="flex-1 flex items-center justify-center p-12">
                <div className="w-6 h-6 border-2 border-blue-600/20 border-t-blue-600 rounded-full animate-spin" />
              </div>
            ) : myTasks.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center p-12 text-center">
                <div className="w-10 h-10 bg-slate-50 text-slate-400 rounded-full flex items-center justify-center mb-3">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <h4 className="text-sm font-semibold text-slate-700">Semua Tugas Selesai!</h4>
                <p className="text-xs text-slate-400 mt-1 max-w-[240px]">
                  Anda tidak memiliki tugas yang mendesak saat ini.
                </p>
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {myTasks.map((task) => (
                  <div
                    key={task.id}
                    onClick={() => onTaskClick(task)}
                    className="flex items-center justify-between px-5 py-3 hover:bg-slate-50 transition-colors cursor-pointer group"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <span className="text-[10px] font-bold text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded shrink-0">
                        {task.key}
                      </span>
                      <span className="text-sm font-semibold text-slate-800 truncate group-hover:text-blue-600 transition-colors">
                        {task.title}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0 ml-4">
                      <span
                        className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${
                          PRIORITY_COLORS[task.priority] || PRIORITY_COLORS.Low
                        }`}
                      >
                        {task.priority}
                      </span>
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${STATUS_BADGES[task.status] || ""}`}>
                        {task.status}
                      </span>
                      <span className="text-[10px] font-semibold text-slate-400 min-w-[70px] text-right">
                        {new Date(task.due_date).toLocaleDateString("id-ID", {
                          day: "numeric",
                          month: "short",
                        })}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Projects (Takes 1 col) */}
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h3 className="text-md font-bold text-slate-800 flex items-center gap-2">
              <span className="w-1.5 h-6 bg-indigo-600 rounded-full" />
              Proyek Saya
            </h3>
          </div>

          <div className="flex flex-col gap-3">
            {loadingProjects ? (
              <div className="bg-white rounded-xl border border-slate-150 shadow-sm p-8 flex items-center justify-center">
                <div className="w-6 h-6 border-2 border-indigo-600/20 border-t-indigo-600 rounded-full animate-spin" />
              </div>
            ) : projects.length === 0 ? (
              <div className="bg-white rounded-xl border border-slate-150 shadow-sm p-8 text-center">
                <p className="text-xs text-slate-400">Anda belum tergabung dalam proyek apa pun.</p>
              </div>
            ) : (
              projects.map((project) => (
                <div
                  key={project.id}
                  onClick={() => onSelectProject(project.id)}
                  className="bg-white rounded-xl border border-slate-150 p-4 shadow-sm hover:shadow-md hover:border-indigo-200 transition-all cursor-pointer flex flex-col gap-2 group"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full uppercase tracking-wider">
                      {project.key}
                    </span>
                    <span className="text-[10px] font-semibold text-slate-400">
                      ID: {project.id}
                    </span>
                  </div>
                  <h4 className="text-sm font-bold text-slate-800 group-hover:text-indigo-600 transition-colors">
                    {project.name}
                  </h4>
                  <div className="flex items-center gap-1.5 mt-1 text-[11px] font-medium text-slate-400">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    Status: {project.status}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
