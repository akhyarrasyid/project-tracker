import React, { useEffect, useState } from "react";
import { useAuth } from "../contexts/useAuth";
import { metaApi } from "../api/meta";
import type { ProjectMeta } from "../types/meta";

interface ProjectSidebarProps {
  selectedProjectId: number | null;
  onSelectProject: (projectId: number | null) => void;
}

export const ProjectSidebar: React.FC<ProjectSidebarProps> = ({
  selectedProjectId,
  onSelectProject,
}) => {
  const { user, logout } = useAuth();
  const [projects, setProjects] = useState<ProjectMeta[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchProjects = async () => {
      try {
        const data = await metaApi.getProjects();
        setProjects(data);
      } catch (err) {
        console.error("Failed to fetch projects for sidebar", err);
      } finally {
        setLoading(false);
      }
    };

    fetchProjects();
  }, []);

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 text-slate-300 flex flex-col justify-between shrink-0 font-sans">
      {/* Upper Section */}
      <div className="flex flex-col gap-6 p-4">
        {/* Brand Logo */}
        <div className="flex items-center gap-3 px-2 py-1">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center shadow-md shadow-blue-500/20">
            <svg className="w-4.5 h-4.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2.5}
                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
              />
            </svg>
          </div>
          <div>
            <h1 className="text-sm font-bold text-white tracking-tight leading-none mb-0.5">Project Tracker</h1>
            <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Enterprise</span>
          </div>
        </div>

        {/* Global Dashboard Navigation */}
        <div className="flex flex-col gap-1">
          <button
            onClick={() => onSelectProject(null)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-bold tracking-wide transition-all cursor-pointer ${
              selectedProjectId === null
                ? "bg-blue-600 text-white shadow-lg shadow-blue-600/15"
                : "hover:bg-slate-800 text-slate-400 hover:text-white"
            }`}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 6a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2H6a2 2 0 01-2-2v-4zM14 16a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2a2 2 0 01-2-2v-4z"
              />
            </svg>
            Dashboard
          </button>
        </div>

        {/* Projects List Section */}
        <div className="flex flex-col gap-2">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider px-3">Proyek Workspace</span>
          {loading ? (
            <div className="flex justify-center py-4">
              <div className="w-4 h-4 border-2 border-slate-700 border-t-slate-400 rounded-full animate-spin" />
            </div>
          ) : (
            <div className="flex flex-col gap-0.5 max-h-[400px] overflow-y-auto">
              {projects.map((project) => (
                <button
                  key={project.id}
                  onClick={() => onSelectProject(project.id)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all cursor-pointer ${
                    selectedProjectId === project.id
                      ? "bg-slate-800 text-white font-bold"
                      : "hover:bg-slate-800/60 text-slate-400 hover:text-white"
                  }`}
                >
                  <span className="truncate max-w-[140px]">{project.name}</span>
                  <span className="text-[8px] font-bold px-1.5 py-0.5 rounded bg-slate-850 text-slate-500 shrink-0">
                    {project.key}
                  </span>
                </button>
              ))}
              {projects.length === 0 && (
                <span className="text-[11px] text-slate-650 px-3 py-2 italic">Belum ada proyek</span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Lower Section (Profile & Logout) */}
      <div className="p-4 border-t border-slate-800 flex flex-col gap-4">
        {/* User Card */}
        <div className="flex items-center gap-3 px-2">
          <div className="w-8 h-8 rounded-full bg-blue-600/10 border border-blue-500/25 flex items-center justify-center font-bold text-blue-400 text-xs shrink-0 uppercase">
            {user?.username.slice(0, 2)}
          </div>
          <div className="min-w-0">
            <h4 className="text-xs font-bold text-white truncate">{user?.full_name}</h4>
            <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wide">
              {user?.role}
            </span>
          </div>
        </div>

        {/* Logout Button */}
        <button
          onClick={logout}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-red-500/10 text-slate-400 hover:text-red-400 text-xs font-bold transition-all cursor-pointer"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
            />
          </svg>
          Keluar
        </button>
      </div>
    </aside>
  );
};
