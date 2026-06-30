import { Bell, Home, LogOut, Search, UserCircle2 } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { getBuildLabel } from "../app/build-info";
import { LoginPage } from "../components/LoginPage";
import { useAuth } from "../contexts/useAuth";
import { useUnreadNotificationCountQuery } from "../features/notifications/hooks/useUnreadNotificationCountQuery";
import { useProjectsQuery } from "../features/projects/hooks/useProjectsQuery";

function cn(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

export function WorkspaceLayout() {
  const { user, loading, logout } = useAuth();
  const projectsQuery = useProjectsQuery();
  const unreadCountQuery = useUnreadNotificationCountQuery();
  const buildLabel = getBuildLabel();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-neutral-100">
        <div className="text-sm font-medium text-neutral-500">Memuat workspace...</div>
      </div>
    );
  }

  if (!user) {
    return <LoginPage />;
  }

  return (
    <div className="flex min-h-screen bg-neutral-100 text-neutral-900">
      <aside className="flex w-60 shrink-0 flex-col border-r border-neutral-200 bg-neutral-950 text-neutral-200">
        <div className="border-b border-neutral-800 px-4 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-sm font-semibold text-white">
              P
            </div>
            <div>
              <div className="text-sm font-semibold text-white">Project Tracker</div>
              <div className="text-[11px] text-neutral-500">Operational workspace</div>
            </div>
          </div>
          <button className="mt-4 flex w-full items-center gap-2 rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2 text-left text-xs text-neutral-500">
            <Search className="h-3.5 w-3.5" />
            Search
          </button>
        </div>

        <nav className="flex flex-1 flex-col gap-6 overflow-y-auto px-3 py-4">
          <div className="space-y-1">
            <NavLink
              to="/inbox"
              className={({ isActive }) =>
                cn(
                  "flex items-center justify-between rounded-md px-3 py-2 text-sm transition-colors",
                  isActive ? "bg-neutral-800 text-white" : "text-neutral-400 hover:bg-neutral-900 hover:text-white",
                )
              }
            >
              <span className="flex items-center gap-2">
                <Bell className="h-4 w-4" />
                Inbox
              </span>
              {unreadCountQuery.data?.unread_count ? (
                <span className="rounded-full bg-neutral-700 px-2 py-0.5 text-[11px] text-white">
                  {unreadCountQuery.data.unread_count > 99
                    ? "99+"
                    : unreadCountQuery.data.unread_count}
                </span>
              ) : null}
            </NavLink>
            <NavLink
              to="/my-issues"
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                  isActive ? "bg-neutral-800 text-white" : "text-neutral-400 hover:bg-neutral-900 hover:text-white",
                )
              }
            >
              <Home className="h-4 w-4" />
              My issues
            </NavLink>
          </div>

          <div className="space-y-2">
            <div className="px-3 text-[11px] font-semibold uppercase tracking-wide text-neutral-500">
              Projects
            </div>
            <div className="space-y-1">
              {projectsQuery.data?.map((project) => (
                <NavLink
                  key={project.id}
                  to={`/projects/${project.key}/board`}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center justify-between rounded-md px-3 py-2 text-sm transition-colors",
                      isActive ? "bg-neutral-800 text-white" : "text-neutral-400 hover:bg-neutral-900 hover:text-white",
                    )
                  }
                >
                  <span className="truncate">{project.name}</span>
                  <span className="text-[10px] text-neutral-500">{project.key}</span>
                </NavLink>
              ))}
              {projectsQuery.isLoading && (
                <div className="px-3 py-2 text-sm text-neutral-500">Memuat proyek...</div>
              )}
            </div>
          </div>
        </nav>

        <div className="border-t border-neutral-800 px-4 py-4">
          <div className="mb-3 flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-neutral-800 text-neutral-200">
              <UserCircle2 className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <div className="truncate text-sm font-medium text-white">{user.full_name}</div>
              <div className="text-[11px] uppercase tracking-wide text-neutral-500">{user.role}</div>
            </div>
          </div>
          <button
            onClick={logout}
            className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-neutral-400 transition-colors hover:bg-neutral-900 hover:text-white"
          >
            <LogOut className="h-4 w-4" />
            Keluar
          </button>
          <div className="mt-3 text-[11px] text-neutral-500" data-testid="build-identity">
            Build {buildLabel}
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <Outlet />
      </div>
    </div>
  );
}
