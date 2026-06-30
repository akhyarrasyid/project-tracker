import {
  Bell,
  Home,
  LogOut,
  MoonStar,
  Search,
  SunMedium,
  UserCircle2,
} from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import projectTrackerLogo from "../assets/logo project tracker.png";
import { getBuildLabel } from "../app/build-info";
import { useTheme } from "../app/theme";
import { LoginPage } from "../components/LoginPage";
import { useAuth } from "../contexts/useAuth";
import { useUnreadNotificationCountQuery } from "../features/notifications/hooks/useUnreadNotificationCountQuery";
import { useProjectsQuery } from "../features/projects/hooks/useProjectsQuery";

function cn(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

export function WorkspaceLayout() {
  const { user, loading, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const projectsQuery = useProjectsQuery();
  const unreadCountQuery = useUnreadNotificationCountQuery();
  const buildLabel = getBuildLabel();

  if (loading) {
    return (
      <div className="app-shell flex min-h-screen items-center justify-center">
        <div className="text-sm font-medium text-[color:var(--app-text-soft)]">Memuat workspace...</div>
      </div>
    );
  }

  if (!user) {
    return <LoginPage />;
  }

  return (
    <div className="app-shell flex min-h-screen">
      <aside className="app-sidebar sticky top-0 flex h-screen w-64 shrink-0 flex-col border-r text-slate-100">
        <div className="border-b border-white/8 px-4 py-4">
          <div className="flex items-center gap-3">
            <img
              src={projectTrackerLogo}
              alt="Project Tracker"
              className="h-10 w-10 rounded-xl bg-white/95 object-cover p-1 shadow-[0_10px_24px_rgba(37,99,235,0.24)]"
            />
            <div>
              <div className="text-sm font-semibold text-white">Project Tracker</div>
              <div className="text-[11px] text-slate-300/72">Operational workspace</div>
            </div>
          </div>

          <div className="mt-4 flex items-center gap-2">
            <button className="flex flex-1 items-center gap-2 rounded-xl border border-white/10 bg-white/[0.06] px-3 py-2.5 text-left text-xs text-slate-300/58 backdrop-blur">
              <Search className="h-3.5 w-3.5" />
              Search
            </button>
            <button
              type="button"
              onClick={toggleTheme}
              className="rounded-xl border border-white/10 bg-white/[0.06] p-2.5 text-slate-100/90 transition hover:bg-white/10"
              aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
              title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            >
              {theme === "dark" ? <SunMedium className="h-4 w-4" /> : <MoonStar className="h-4 w-4" />}
            </button>
          </div>
        </div>

        <nav className="app-scrollbar flex min-h-0 flex-1 flex-col gap-6 overflow-y-auto px-3 py-4">
          <div className="space-y-1">
            <NavLink
              to="/inbox"
              className={({ isActive }) =>
                cn(
                  "flex items-center justify-between rounded-xl px-3 py-2.5 text-sm transition-colors",
                  isActive
                    ? "bg-white/12 text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]"
                    : "text-slate-300/80 hover:bg-white/8 hover:text-white",
                )
              }
            >
              <span className="flex items-center gap-2">
                <Bell className="h-4 w-4" />
                Inbox
              </span>
              {unreadCountQuery.data?.unread_count ? (
                <span className="rounded-full bg-blue-500/18 px-2 py-0.5 text-[11px] font-medium text-blue-100">
                  {unreadCountQuery.data.unread_count > 99 ? "99+" : unreadCountQuery.data.unread_count}
                </span>
              ) : null}
            </NavLink>
            <NavLink
              to="/my-issues"
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm transition-colors",
                  isActive
                    ? "bg-white/12 text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]"
                    : "text-slate-300/80 hover:bg-white/8 hover:text-white",
                )
              }
            >
              <Home className="h-4 w-4" />
              My issues
            </NavLink>
          </div>

          <div className="space-y-2">
            <div className="px-3 text-[11px] font-semibold tracking-[0.18em] text-slate-300/45">
              Projects
            </div>
            <div className="space-y-1">
              {projectsQuery.data?.map((project) => (
                <NavLink
                  key={project.id}
                  to={`/projects/${project.key}/board`}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center justify-between rounded-xl px-3 py-2.5 text-sm transition-colors",
                      isActive
                        ? "bg-white/12 text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]"
                        : "text-slate-300/80 hover:bg-white/8 hover:text-white",
                    )
                  }
                >
                  <span className="truncate">{project.name}</span>
                  <span className="rounded-full bg-white/5 px-1.5 py-0.5 text-[10px] text-slate-300/55">
                    {project.key}
                  </span>
                </NavLink>
              ))}
              {projectsQuery.isLoading && (
                <div className="px-3 py-2 text-sm text-slate-300/58">Memuat proyek...</div>
              )}
            </div>
          </div>
        </nav>

        <div className="border-t border-white/8 px-4 py-4">
          <div className="mb-3 flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-white/10 text-slate-100">
              <UserCircle2 className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <div className="truncate text-sm font-medium text-white">{user.full_name}</div>
              <div className="text-[11px] tracking-[0.18em] text-slate-300/45">{user.role}</div>
            </div>
          </div>
          <button
            onClick={logout}
            className="flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-sm text-slate-300/80 transition-colors hover:bg-white/8 hover:text-white"
          >
            <LogOut className="h-4 w-4" />
            Keluar
          </button>
          <div className="mt-3 text-[11px] text-slate-300/45" data-testid="build-identity">
            {buildLabel}
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <Outlet />
      </div>
    </div>
  );
}
