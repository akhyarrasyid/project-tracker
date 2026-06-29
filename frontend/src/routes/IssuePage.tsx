import { ArrowLeft } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";

import { IssueDetailPanel } from "../features/issues/components/IssueDetailPanel";

export function IssuePage() {
  const { issueKey } = useParams();
  const navigate = useNavigate();

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="inline-flex items-center gap-2 rounded-md border border-neutral-200 px-3 py-2 text-sm text-neutral-600 hover:bg-neutral-50"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>
      </div>
      <IssueDetailPanel issueKey={issueKey} onClose={() => navigate(-1)} />
    </div>
  );
}
