import { useNavigate } from "react-router-dom";

import { useAuth } from "../contexts/useAuth";
import { useMyIssuesQuery } from "../features/issues/hooks/useMyIssuesQuery";

export function MyIssuesPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const issuesQuery = useMyIssuesQuery(user?.id);

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
      <div>
        <div className="text-xs font-medium tracking-[0.18em] text-[color:var(--app-text-soft)]">My work</div>
        <h1 className="app-heading mt-1 text-3xl font-semibold">Assigned issues</h1>
      </div>

      <div className="app-panel overflow-hidden rounded-[24px]">
        <div className="grid grid-cols-[140px_minmax(0,1fr)_160px_140px] gap-4 border-b border-[color:var(--app-border)] px-5 py-3 text-[11px] font-semibold tracking-[0.16em] text-[color:var(--app-text-soft)]">
          <div>Issue</div>
          <div>Summary</div>
          <div>Status</div>
          <div>Due date</div>
        </div>
        {issuesQuery.isLoading && <div className="px-5 py-6 text-sm text-[color:var(--app-text-soft)]">Memuat issue...</div>}
        {issuesQuery.data?.items.map((issue) => (
          <button
            key={issue.id}
            type="button"
            onClick={() => navigate(`/issues/${issue.key}`)}
            className="grid w-full grid-cols-[140px_minmax(0,1fr)_160px_140px] gap-4 border-b border-[color:var(--app-border)] px-5 py-4 text-left text-sm hover:bg-[color:var(--app-panel-muted)]/80"
          >
            <div className="font-medium text-blue-600">{issue.key}</div>
            <div className="truncate text-[color:var(--app-heading)]">{issue.title}</div>
            <div className="text-[color:var(--app-text-soft)]">{issue.status}</div>
            <div className="text-[color:var(--app-text-soft)]">{issue.due_date}</div>
          </button>
        ))}
        {!issuesQuery.isLoading && !issuesQuery.data?.items.length && (
          <div className="px-5 py-10 text-sm text-[color:var(--app-text-soft)]">Belum ada issue yang di-assign ke Anda.</div>
        )}
      </div>
    </div>
  );
}
