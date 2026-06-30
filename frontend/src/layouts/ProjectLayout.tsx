import { AlertCircle, CheckCircle2, Clock3, KanbanSquare, List, CalendarDays } from "lucide-react";
import { NavLink, Outlet, useParams } from "react-router-dom";

import { useProjectByKeyQuery } from "../features/projects/hooks/useProjectByKeyQuery";
import { useProjectSummaryQuery } from "../features/projects/hooks/useProjectSummaryQuery";

function cn(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

export function ProjectLayout() {
  const { projectKey } = useParams();
  const projectQuery = useProjectByKeyQuery(projectKey);
  const summaryQuery = useProjectSummaryQuery(projectQuery.data?.id);

  if (projectQuery.isLoading) {
    return <div className="p-8 text-sm text-neutral-500">Memuat proyek...</div>;
  }

  if (!projectQuery.data) {
    return <div className="p-8 text-sm text-neutral-500">Proyek tidak ditemukan.</div>;
  }

  const project = projectQuery.data;
  const summary = summaryQuery.data;

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-neutral-200 bg-white">
        <div className="flex flex-col gap-4 px-8 py-6">
          <div className="flex items-start justify-between gap-6">
            <div className="min-w-0">
              <div className="text-xs font-medium uppercase tracking-wide text-neutral-500">
                Project / {project.key}
              </div>
              <h1 className="mt-1 text-2xl font-semibold text-neutral-900">{project.name}</h1>
            </div>

            {summary && (
              <div className="grid grid-cols-4 gap-3">
                <div className="rounded-md border border-neutral-200 px-3 py-2">
                  <div className="flex items-center gap-2 text-[11px] uppercase tracking-wide text-neutral-500">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    Progress
                  </div>
                  <div className="mt-1 text-sm font-semibold text-neutral-900">
                    {summary.issue_progress_percent}%
                  </div>
                </div>
                <div className="rounded-md border border-neutral-200 px-3 py-2">
                  <div className="flex items-center gap-2 text-[11px] uppercase tracking-wide text-neutral-500">
                    <Clock3 className="h-3.5 w-3.5" />
                    Active
                  </div>
                  <div className="mt-1 text-sm font-semibold text-neutral-900">{summary.active_issues}</div>
                </div>
                <div className="rounded-md border border-neutral-200 px-3 py-2">
                  <div className="flex items-center gap-2 text-[11px] uppercase tracking-wide text-neutral-500">
                    <AlertCircle className="h-3.5 w-3.5" />
                    Blocked
                  </div>
                  <div className="mt-1 text-sm font-semibold text-neutral-900">{summary.blocked_count}</div>
                </div>
                <div className="rounded-md border border-neutral-200 px-3 py-2">
                  <div className="flex items-center gap-2 text-[11px] uppercase tracking-wide text-neutral-500">
                    <AlertCircle className="h-3.5 w-3.5" />
                    At risk
                  </div>
                  <div className="mt-1 text-sm font-semibold text-neutral-900">{summary.at_risk_count}</div>
                </div>
              </div>
            )}
          </div>

          <nav className="flex items-center gap-2">
            <NavLink
              to={`/projects/${project.key}/board`}
              className={({ isActive }) =>
                cn(
                  "inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                  isActive ? "bg-neutral-900 text-white" : "text-neutral-600 hover:bg-neutral-100",
                )
              }
            >
              <KanbanSquare className="h-4 w-4" />
              Board
            </NavLink>
            <NavLink
              to={`/projects/${project.key}/issues`}
              className={({ isActive }) =>
                cn(
                  "inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                  isActive ? "bg-neutral-900 text-white" : "text-neutral-600 hover:bg-neutral-100",
                )
              }
            >
              <List className="h-4 w-4" />
              Issues
            </NavLink>
            <NavLink
              to={`/projects/${project.key}/calendar`}
              className={({ isActive }) =>
                cn(
                  "inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                  isActive ? "bg-neutral-900 text-white" : "text-neutral-600 hover:bg-neutral-100",
                )
              }
            >
              <CalendarDays className="h-4 w-4" />
              Calendar
            </NavLink>
          </nav>
        </div>
      </header>

      <main className="min-h-0 flex-1 overflow-y-auto p-8">
        <Outlet />
      </main>
    </div>
  );
}
