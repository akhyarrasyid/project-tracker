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
        <div className="text-xs font-medium uppercase tracking-wide text-neutral-500">My work</div>
        <h1 className="mt-1 text-2xl font-semibold text-neutral-900">Assigned issues</h1>
      </div>

      <div className="overflow-hidden rounded-lg border border-neutral-200 bg-white">
        <div className="grid grid-cols-[140px_minmax(0,1fr)_140px_120px] gap-4 border-b border-neutral-200 px-5 py-3 text-xs font-medium uppercase tracking-wide text-neutral-500">
          <div>Issue</div>
          <div>Summary</div>
          <div>Status</div>
          <div>Due date</div>
        </div>
        {issuesQuery.isLoading && <div className="px-5 py-6 text-sm text-neutral-500">Memuat issue...</div>}
        {issuesQuery.data?.items.map((issue) => (
          <button
            key={issue.id}
            type="button"
            onClick={() => navigate(`/issues/${issue.key}`)}
            className="grid w-full grid-cols-[140px_minmax(0,1fr)_140px_120px] gap-4 border-b border-neutral-100 px-5 py-4 text-left text-sm hover:bg-neutral-50"
          >
            <div className="font-medium text-blue-600">{issue.key}</div>
            <div className="truncate text-neutral-900">{issue.title}</div>
            <div className="text-neutral-600">{issue.status}</div>
            <div className="text-neutral-600">{issue.due_date}</div>
          </button>
        ))}
        {!issuesQuery.isLoading && !issuesQuery.data?.items.length && (
          <div className="px-5 py-10 text-sm text-neutral-500">Belum ada issue yang di-assign ke Anda.</div>
        )}
      </div>
    </div>
  );
}
