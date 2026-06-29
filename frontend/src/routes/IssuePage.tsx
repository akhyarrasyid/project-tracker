import { ArrowLeft, AlertCircle } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { useIssueQuery } from "../features/issues/hooks/useIssueQuery";

export function IssuePage() {
  const { issueKey } = useParams();
  const issueQuery = useIssueQuery(issueKey);

  if (issueQuery.isLoading) {
    return <div className="p-8 text-sm text-neutral-500">Memuat issue...</div>;
  }

  if (!issueQuery.data) {
    return <div className="p-8 text-sm text-neutral-500">Issue tidak ditemukan.</div>;
  }

  const issue = issueQuery.data;

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
      <div className="flex items-center gap-3">
        <Link
          to={issue.project_key ? `/projects/${issue.project_key}/board` : "/my-issues"}
          className="inline-flex items-center gap-2 rounded-md border border-neutral-200 px-3 py-2 text-sm text-neutral-600 hover:bg-neutral-50"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </Link>
        <div className="text-sm font-medium text-blue-600">{issue.key}</div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <section className="rounded-lg border border-neutral-200 bg-white p-6">
          <h1 className="text-2xl font-semibold text-neutral-900">{issue.title}</h1>
          <p className="mt-4 whitespace-pre-wrap text-sm leading-6 text-neutral-600">
            {issue.description || "Belum ada deskripsi."}
          </p>
        </section>

        <aside className="rounded-lg border border-neutral-200 bg-white p-6">
          <div className="mb-4 text-xs font-medium uppercase tracking-wide text-neutral-500">
            Properties
          </div>
          <dl className="space-y-4 text-sm">
            <div className="flex items-start justify-between gap-4">
              <dt className="text-neutral-500">Status</dt>
              <dd className="text-right font-medium text-neutral-900">{issue.status}</dd>
            </div>
            <div className="flex items-start justify-between gap-4">
              <dt className="text-neutral-500">Priority</dt>
              <dd className="text-right font-medium text-neutral-900">{issue.priority}</dd>
            </div>
            <div className="flex items-start justify-between gap-4">
              <dt className="text-neutral-500">Assignee</dt>
              <dd className="text-right font-medium text-neutral-900">{issue.assignee || "Unassigned"}</dd>
            </div>
            <div className="flex items-start justify-between gap-4">
              <dt className="text-neutral-500">Due date</dt>
              <dd className="text-right font-medium text-neutral-900">{issue.due_date}</dd>
            </div>
            <div className="flex items-start justify-between gap-4">
              <dt className="text-neutral-500">Estimate</dt>
              <dd className="text-right font-medium text-neutral-900">{issue.estimated_hours}h</dd>
            </div>
            {issue.is_blocked && (
              <div className="rounded-md border border-red-200 bg-red-50 p-3 text-red-700">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide">
                  <AlertCircle className="h-4 w-4" />
                  Blocked
                </div>
                <div className="mt-2 text-sm">
                  {issue.blocked_reason || "Issue ini sedang diblokir."}
                </div>
              </div>
            )}
          </dl>
        </aside>
      </div>
    </div>
  );
}
