import {
  AlertCircle,
  CalendarDays,
  CheckCircle2,
  Clock3,
  KanbanSquare,
  List,
} from "lucide-react";
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
    return <div className="p-8 text-sm text-[color:var(--app-text-soft)]">Memuat proyek...</div>;
  }

  if (!projectQuery.data) {
    return <div className="p-8 text-sm text-[color:var(--app-text-soft)]">Proyek tidak ditemukan.</div>;
  }

  const project = projectQuery.data;
  const summary = summaryQuery.data;

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-[color:var(--app-border)] bg-[color:var(--app-panel)] backdrop-blur">
        <div className="flex flex-col gap-4 px-8 py-6">
          <div className="flex items-start justify-between gap-6">
            <div className="min-w-0">
              <div className="text-xs font-medium tracking-[0.18em] text-[color:var(--app-text-soft)]">
                Project / {project.key}
              </div>
              <h1 className="app-heading mt-1 text-3xl font-semibold">{project.name}</h1>
            </div>

            {summary && (
              <div className="grid grid-cols-4 gap-3">
                <MetricCard icon={CheckCircle2} label="Progress" value={`${summary.issue_progress_percent}%`} />
                <MetricCard icon={Clock3} label="Active" value={String(summary.active_issues)} />
                <MetricCard icon={AlertCircle} label="Blocked" value={String(summary.blocked_count)} />
                <MetricCard icon={AlertCircle} label="At risk" value={String(summary.at_risk_count)} />
              </div>
            )}
          </div>

          <nav className="flex items-center gap-2">
            <ProjectNavLink to={`/projects/${project.key}/board`} icon={KanbanSquare}>
              Board
            </ProjectNavLink>
            <ProjectNavLink to={`/projects/${project.key}/issues`} icon={List}>
              Issues
            </ProjectNavLink>
            <ProjectNavLink to={`/projects/${project.key}/calendar`} icon={CalendarDays}>
              Calendar
            </ProjectNavLink>
          </nav>
        </div>
      </header>

      <main className="app-shell app-scrollbar min-h-0 flex-1 overflow-y-auto p-8">
        <Outlet />
      </main>
    </div>
  );
}

function MetricCard({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof CheckCircle2;
  label: string;
  value: string;
}) {
  return (
    <div className="app-card rounded-2xl px-3.5 py-3">
      <div className="flex items-center gap-2 text-[11px] font-medium tracking-[0.16em] text-[color:var(--app-text-soft)]">
        <Icon className="h-3.5 w-3.5" />
        {label}
      </div>
      <div className="app-heading mt-1 text-base font-semibold">{value}</div>
    </div>
  );
}

function ProjectNavLink({
  to,
  icon: Icon,
  children,
}: {
  to: string;
  icon: typeof KanbanSquare;
  children: string;
}) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cn(
          "inline-flex items-center gap-2 rounded-xl px-3.5 py-2.5 text-sm transition-colors",
          isActive
            ? "bg-[color:var(--app-heading)] text-white shadow-[0_10px_20px_rgba(15,23,42,0.12)]"
            : "text-[color:var(--app-text-soft)] hover:bg-[color:var(--app-panel-muted)]",
        )
      }
    >
      <Icon className="h-4 w-4" />
      {children}
    </NavLink>
  );
}
