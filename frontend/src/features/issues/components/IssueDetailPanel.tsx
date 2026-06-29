import { useMutation, useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  CalendarDays,
  Check,
  ChevronDown,
  LoaderCircle,
  MoreHorizontal,
  Trash2,
  X,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { issueApi } from "../../../api/issues";
import { metaApi } from "../../../api/meta";
import { taskApi } from "../../../api/tasks";
import { queryClient } from "../../../app/query-client";
import { useIssueQuery } from "../hooks/useIssueQuery";
import type {
  IssueActivity,
  IssuePatchInput,
  IssueComment,
  Task,
  TaskPriority,
  TaskStatus,
  TaskUpdate,
} from "../../../types/task";

type SaveState = "idle" | "saving" | "saved" | "error";

interface Props {
  issueKey?: string;
  mode?: "sheet" | "page";
  onClose?: () => void;
}

const STATUS_OPTIONS: TaskStatus[] = ["Todo", "In Progress", "Review", "Done"];
const PRIORITY_OPTIONS: TaskPriority[] = ["Low", "Medium", "High", "Critical"];

function cn(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

function describeActivity(item: IssueActivity) {
  if (item.field && item.old_value && item.new_value) {
    return `${item.actor.full_name} changed ${item.field} from ${item.old_value} to ${item.new_value}`;
  }
  if (item.field && item.new_value) {
    return `${item.actor.full_name} updated ${item.field} to ${item.new_value}`;
  }
  return `${item.actor.full_name} ${item.action.toLowerCase()}`;
}

function getConflictMessage(error: unknown) {
  const detail = (error as { response?: { data?: { detail?: { message?: string } } } })?.response?.data?.detail;
  return detail?.message ?? null;
}

function getLatestIssue(error: unknown) {
  const detail = (error as { response?: { data?: { detail?: { latest_issue?: Task } } } })?.response?.data?.detail;
  return detail?.latest_issue ?? null;
}

export function IssueDetailPanel({ issueKey, mode = "page", onClose }: Props) {
  const issueQuery = useIssueQuery(issueKey);
  const issue = issueQuery.data;
  const issueId = issue?.id;
  const [draft, setDraft] = useState<Task | null>(null);
  const [descriptionDraft, setDescriptionDraft] = useState("");
  const [commentDraft, setCommentDraft] = useState("");
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const [titleTouched, setTitleTouched] = useState(false);
  const saveResetRef = useRef<number | null>(null);
  const titleDebounceRef = useRef<number | null>(null);
  const patchQueueRef = useRef(Promise.resolve<Task | null>(null));

  const usersQuery = useQuery({
    queryKey: ["project-users", issue?.project_id],
    queryFn: () => metaApi.getUsers(issue!.project_id),
    enabled: Boolean(issue?.project_id),
  });

  const commentsQuery = useQuery({
    queryKey: ["issue-comments", issueId],
    queryFn: () => issueApi.getComments(issueId!),
    enabled: typeof issueId === "number",
  });

  const activitiesQuery = useQuery({
    queryKey: ["issue-activities", issueId],
    queryFn: () => issueApi.getActivities(issueId!),
    enabled: typeof issueId === "number",
  });

  const subIssuesQuery = useQuery({
    queryKey: ["issue-subissues", issue?.project_id],
    queryFn: () =>
      taskApi.getAll({
        project_id: issue!.project_id,
        page: 1,
        size: 100,
        sort_by: "created_at",
        sort_order: "asc",
      }),
    enabled: Boolean(issue?.project_id),
  });

  useEffect(() => {
    if (!issue) {
      return;
    }
    setDraft(issue);
    setDescriptionDraft(issue.description);
    setTitleTouched(false);
  }, [issue]);

  useEffect(() => {
    return () => {
      if (titleDebounceRef.current) {
        window.clearTimeout(titleDebounceRef.current);
      }
      if (saveResetRef.current) {
        window.clearTimeout(saveResetRef.current);
      }
    };
  }, []);

  const subIssues = useMemo(
    () =>
      (subIssuesQuery.data?.items ?? []).filter((candidate) => candidate.parent_id === issue?.id),
    [issue?.id, subIssuesQuery.data?.items],
  );

  function scheduleSaveReset(nextState: SaveState) {
    if (saveResetRef.current) {
      window.clearTimeout(saveResetRef.current);
    }
    if (nextState === "saved") {
      saveResetRef.current = window.setTimeout(() => {
        setSaveState("idle");
        setSaveMessage(null);
      }, 1200);
    }
  }

  function syncIssue(nextIssue: Task) {
    queryClient.setQueryData(["issue", issueKey], nextIssue);
    setDraft(nextIssue);
    setDescriptionDraft(nextIssue.description);
  }

  function rollbackIssue(previousIssue: Task) {
    queryClient.setQueryData(["issue", issueKey], previousIssue);
    setDraft(previousIssue);
    setDescriptionDraft(previousIssue.description);
  }

  function invalidateIssueSurfaces(nextIssue: Task) {
    void queryClient.invalidateQueries({ queryKey: ["issue-activities", nextIssue.id] });
    void queryClient.invalidateQueries({ queryKey: ["my-issues"] });
    if (nextIssue.project_key) {
      void queryClient.invalidateQueries({ queryKey: ["board", nextIssue.project_key] });
    }
  }

  function enqueuePatch(patch: Partial<TaskUpdate>) {
    if (!issueKey) {
      return Promise.resolve<Task | null>(null);
    }

    patchQueueRef.current = patchQueueRef.current
      .catch(() => null)
      .then(async () => {
        const currentIssue = queryClient.getQueryData<Task>(["issue", issueKey]);
        if (!currentIssue) {
          return null;
        }

        const hasChanges = Object.entries(patch).some(([field, value]) => {
          return currentIssue[field as keyof Task] !== value;
        });
        if (!hasChanges) {
          return currentIssue;
        }

        const previousIssue = currentIssue;
        const optimisticIssue = { ...currentIssue, ...patch } as Task;
        queryClient.setQueryData(["issue", issueKey], optimisticIssue);
        setDraft(optimisticIssue);
        if (Object.prototype.hasOwnProperty.call(patch, "description")) {
          setDescriptionDraft(String(patch.description ?? ""));
        }
        setSaveState("saving");
        setSaveMessage(null);

        try {
          const updatedIssue = await issueApi.patch(currentIssue.id, {
            ...(patch as TaskUpdate),
            expected_version: currentIssue.version,
          } satisfies IssuePatchInput);
          syncIssue(updatedIssue);
          setSaveState("saved");
          scheduleSaveReset("saved");
          invalidateIssueSurfaces(updatedIssue);
          return updatedIssue;
        } catch (error) {
          const latestIssue = getLatestIssue(error);
          if (latestIssue) {
            syncIssue(latestIssue);
            setSaveMessage(
              getConflictMessage(error) ||
                "Perubahan terbaru ditemukan. Review data terbaru sebelum menyimpan lagi.",
            );
          } else {
            rollbackIssue(previousIssue);
            setSaveMessage("Perubahan belum tersimpan. Coba lagi.");
          }
          setSaveState("error");
          return latestIssue;
        }
      });

    return patchQueueRef.current;
  }

  const deleteMutation = useMutation({
    mutationFn: () => issueApi.deleteById(issueId!),
    onSuccess: async () => {
      if (issueKey) {
        queryClient.removeQueries({ queryKey: ["issue", issueKey] });
      }
      await queryClient.invalidateQueries({ queryKey: ["my-issues"] });
      if (draft?.project_key) {
        await queryClient.invalidateQueries({ queryKey: ["board", draft.project_key] });
      }
      setShowDeleteDialog(false);
      onClose?.();
    },
  });

  const commentMutation = useMutation({
    mutationFn: () => issueApi.createComment(issueId!, commentDraft.trim()),
    onSuccess: async (comment) => {
      setCommentDraft("");
      queryClient.setQueryData<IssueComment[]>(["issue-comments", issueId], (current = []) => [
        ...current,
        comment,
      ]);
      await queryClient.invalidateQueries({ queryKey: ["issue", issueKey] });
      await queryClient.invalidateQueries({ queryKey: ["issue-activities", issueId] });
      if (draft?.project_key) {
        await queryClient.invalidateQueries({ queryKey: ["board", draft.project_key] });
      }
    },
  });

  if (!issueKey) {
    return null;
  }

  const panelBody = (() => {
    if (issueQuery.isLoading || !draft) {
      return (
        <div className="flex h-full items-center justify-center text-sm text-neutral-500">
          <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
          Memuat issue...
        </div>
      );
    }

    const dueDateValue = draft.due_date ? draft.due_date.slice(0, 10) : "";

    return (
      <div className="flex h-full flex-col bg-white">
        <div className="border-b border-neutral-200 px-5 py-4">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0 flex-1">
              <div className="text-[12px] text-neutral-500">{draft.key}</div>
              <input
                aria-label="Issue title"
                value={draft.title}
                onChange={(event) => {
                  const nextTitle = event.target.value;
                  setTitleTouched(true);
                  setDraft((current) => (current ? { ...current, title: nextTitle } : current));
                  if (titleDebounceRef.current) {
                    window.clearTimeout(titleDebounceRef.current);
                  }
                  titleDebounceRef.current = window.setTimeout(() => {
                    const trimmedTitle = nextTitle.trim();
                    if (!trimmedTitle) {
                      rollbackIssue(issueQuery.data ?? draft);
                      return;
                    }
                    void enqueuePatch({ title: trimmedTitle });
                  }, 400);
                }}
                onBlur={() => {
                  if (!titleTouched) {
                    return;
                  }
                  const trimmedTitle = draft.title.trim();
                  if (!trimmedTitle) {
                    rollbackIssue(issueQuery.data ?? draft);
                    return;
                  }
                  void enqueuePatch({ title: trimmedTitle });
                }}
                className="mt-1 w-full border-0 bg-transparent p-0 text-[22px] font-semibold leading-7 text-neutral-950 outline-none"
              />
            </div>

            <div className="relative flex items-center gap-2">
              <button
                type="button"
                onClick={() => setMenuOpen((current) => !current)}
                className="rounded-md border border-neutral-200 p-2 text-neutral-500 hover:bg-neutral-50 hover:text-neutral-900"
                aria-label="Issue actions"
              >
                <MoreHorizontal className="h-4 w-4" />
              </button>
              {menuOpen ? (
                <div className="absolute right-0 top-11 z-10 min-w-44 rounded-md border border-neutral-200 bg-white p-1 shadow-sm">
                  <button
                    type="button"
                    onClick={() => {
                      setMenuOpen(false);
                      setShowDeleteDialog(true);
                    }}
                    className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-red-600 hover:bg-red-50"
                  >
                    <Trash2 className="h-4 w-4" />
                    Delete issue
                  </button>
                </div>
              ) : null}
              {onClose ? (
                <button
                  type="button"
                  onClick={onClose}
                  className="rounded-md border border-neutral-200 p-2 text-neutral-500 hover:bg-neutral-50 hover:text-neutral-900"
                  aria-label="Close issue"
                >
                  <X className="h-4 w-4" />
                </button>
              ) : null}
            </div>
          </div>

          <div className="mt-3 flex items-center gap-3 text-[12px] text-neutral-500">
            {saveState === "saving" ? <span>Saving...</span> : null}
            {saveState === "saved" ? (
              <span className="inline-flex items-center gap-1 text-emerald-600">
                <Check className="h-3.5 w-3.5" />
                Saved
              </span>
            ) : null}
            {saveState === "error" && saveMessage ? (
              <span className="inline-flex items-center gap-1 text-amber-700">
                <AlertCircle className="h-3.5 w-3.5" />
                {saveMessage}
              </span>
            ) : null}
          </div>
        </div>

        <div className="grid min-h-0 flex-1 gap-0 lg:grid-cols-[minmax(0,1fr)_280px]">
          <div className="min-h-0 overflow-y-auto px-5 py-5">
            <section>
              <div className="mb-2 text-[12px] font-medium text-neutral-500">Description</div>
              <textarea
                aria-label="Issue description"
                value={descriptionDraft}
                onChange={(event) => setDescriptionDraft(event.target.value)}
                rows={6}
                className="w-full rounded-md border border-neutral-200 px-3 py-2 text-sm leading-6 text-neutral-800 outline-none focus:border-neutral-400"
                placeholder="Tambahkan konteks issue di sini..."
              />
              <div className="mt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setDescriptionDraft(draft.description)}
                  className="rounded-md border border-neutral-200 px-3 py-2 text-sm text-neutral-600 hover:bg-neutral-50"
                >
                  Reset
                </button>
                <button
                  type="button"
                  onClick={() => void enqueuePatch({ description: descriptionDraft })}
                  className="rounded-md bg-neutral-900 px-3 py-2 text-sm text-white hover:bg-neutral-800"
                >
                  Save description
                </button>
              </div>
            </section>

            <section className="mt-6 border-t border-neutral-200 pt-6">
              <div className="mb-3 text-[12px] font-medium text-neutral-500">Sub-issues</div>
              {subIssues.length ? (
                <div className="space-y-2">
                  {subIssues.map((item) => (
                    <div
                      key={item.id}
                      className="rounded-md border border-neutral-200 px-3 py-2 text-sm text-neutral-700"
                    >
                      <div className="text-[12px] text-neutral-500">{item.key}</div>
                      <div className="mt-1">{item.title}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded-md border border-dashed border-neutral-200 px-3 py-3 text-sm text-neutral-500">
                  Belum ada sub-issue.
                </div>
              )}
            </section>

            <section className="mt-6 border-t border-neutral-200 pt-6">
              <div className="mb-3 text-[12px] font-medium text-neutral-500">Comments</div>
              <div className="space-y-3">
                {commentsQuery.data?.length ? (
                  commentsQuery.data.map((comment) => (
                    <div
                      key={comment.id}
                      className="rounded-md border border-neutral-200 px-3 py-3 text-sm"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="font-medium text-neutral-900">{comment.author.full_name}</div>
                        <div className="text-[12px] text-neutral-500">{new Date(comment.created_at).toLocaleString("id-ID")}</div>
                      </div>
                      <div className="mt-2 whitespace-pre-wrap text-neutral-700">{comment.content}</div>
                    </div>
                  ))
                ) : (
                  <div className="rounded-md border border-dashed border-neutral-200 px-3 py-3 text-sm text-neutral-500">
                    Belum ada komentar.
                  </div>
                )}
              </div>
              <div className="mt-4 rounded-md border border-neutral-200 p-3">
                <textarea
                  aria-label="New comment"
                  value={commentDraft}
                  onChange={(event) => setCommentDraft(event.target.value)}
                  rows={3}
                  className="w-full resize-none border-0 p-0 text-sm text-neutral-800 outline-none"
                  placeholder="Tambahkan komentar..."
                />
                <div className="mt-3 flex justify-end">
                  <button
                    type="button"
                    disabled={!commentDraft.trim() || commentMutation.isPending}
                    onClick={() => commentMutation.mutate()}
                    className="rounded-md bg-neutral-900 px-3 py-2 text-sm text-white disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {commentMutation.isPending ? "Posting..." : "Post comment"}
                  </button>
                </div>
              </div>
            </section>

            <section className="mt-6 border-t border-neutral-200 pt-6">
              <div className="mb-3 text-[12px] font-medium text-neutral-500">Activity</div>
              <div className="space-y-3">
                {activitiesQuery.data?.length ? (
                  activitiesQuery.data.map((item) => (
                    <div key={item.id} className="flex gap-3 text-sm">
                      <div className="mt-1 h-2 w-2 rounded-full bg-neutral-300" />
                      <div className="min-w-0 flex-1">
                        <div className="text-neutral-800">{describeActivity(item)}</div>
                        <div className="mt-1 text-[12px] text-neutral-500">
                          {new Date(item.created_at).toLocaleString("id-ID")}
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="rounded-md border border-dashed border-neutral-200 px-3 py-3 text-sm text-neutral-500">
                    Aktivitas akan muncul setelah issue berubah.
                  </div>
                )}
              </div>
            </section>
          </div>

          <aside className="min-h-0 overflow-y-auto border-l border-neutral-200 px-5 py-5">
            <div className="space-y-4 text-sm">
              <label className="block">
                <div className="mb-1 text-[12px] text-neutral-500">Status</div>
                <select
                  aria-label="Issue status"
                  value={draft.status}
                  onChange={(event) =>
                    void enqueuePatch({ status: event.target.value as TaskStatus })
                  }
                  className="w-full rounded-md border border-neutral-200 px-3 py-2 text-sm outline-none focus:border-neutral-400"
                >
                  {STATUS_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block">
                <div className="mb-1 text-[12px] text-neutral-500">Priority</div>
                <select
                  aria-label="Issue priority"
                  value={draft.priority}
                  onChange={(event) =>
                    void enqueuePatch({ priority: event.target.value as TaskPriority })
                  }
                  className="w-full rounded-md border border-neutral-200 px-3 py-2 text-sm outline-none focus:border-neutral-400"
                >
                  {PRIORITY_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block">
                <div className="mb-1 text-[12px] text-neutral-500">Assignee</div>
                <select
                  aria-label="Issue assignee"
                  value={draft.assignee_id ?? ""}
                  onChange={(event) =>
                    void enqueuePatch({
                      assignee_id: event.target.value ? Number(event.target.value) : null,
                    })
                  }
                  className="w-full rounded-md border border-neutral-200 px-3 py-2 text-sm outline-none focus:border-neutral-400"
                >
                  <option value="">Unassigned</option>
                  {(usersQuery.data ?? []).map((user) => (
                    <option key={user.id} value={user.id}>
                      {user.full_name}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block">
                <div className="mb-1 text-[12px] text-neutral-500">Cycle</div>
                <div className="rounded-md border border-neutral-200 px-3 py-2 text-neutral-700">
                  {draft.sprint || "No cycle"}
                </div>
              </label>

              <label className="block">
                <div className="mb-1 text-[12px] text-neutral-500">Due date</div>
                <div className="relative">
                  <CalendarDays className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
                  <input
                    aria-label="Issue due date"
                    type="date"
                    value={dueDateValue}
                    onChange={(event) => void enqueuePatch({ due_date: event.target.value })}
                    className="w-full rounded-md border border-neutral-200 py-2 pl-9 pr-3 text-sm outline-none focus:border-neutral-400"
                  />
                </div>
              </label>

              <label className="block">
                <div className="mb-1 text-[12px] text-neutral-500">Estimate</div>
                <div className="rounded-md border border-neutral-200 px-3 py-2 text-neutral-700">
                  {draft.estimated_hours}h
                </div>
              </label>

              <div>
                <div className="mb-1 text-[12px] text-neutral-500">Labels</div>
                <div className="flex flex-wrap gap-2">
                  {draft.tags.length ? (
                    draft.tags.map((tag) => (
                      <span
                        key={tag}
                        className="rounded-md border border-neutral-200 px-2 py-1 text-[12px] text-neutral-700"
                      >
                        {tag}
                      </span>
                    ))
                  ) : (
                    <span className="text-[12px] text-neutral-500">No labels</span>
                  )}
                </div>
              </div>

              <label className="block">
                <div className="mb-1 text-[12px] text-neutral-500">Blocked</div>
                <label className="inline-flex items-center gap-2 text-sm text-neutral-700">
                  <input
                    aria-label="Issue blocked"
                    type="checkbox"
                    checked={draft.is_blocked}
                    onChange={(event) => {
                      const nextBlocked = event.target.checked;
                      void enqueuePatch({
                        is_blocked: nextBlocked,
                        blocked_reason: nextBlocked ? draft.blocked_reason ?? "" : null,
                      });
                    }}
                  />
                  Mark issue as blocked
                </label>
              </label>

              <label className="block">
                <div className="mb-1 text-[12px] text-neutral-500">Blocked reason</div>
                <textarea
                  aria-label="Blocked reason"
                  value={draft.blocked_reason ?? ""}
                  onChange={(event) =>
                    setDraft((current) =>
                      current ? { ...current, blocked_reason: event.target.value } : current,
                    )
                  }
                  onBlur={() =>
                    void enqueuePatch({ blocked_reason: draft.blocked_reason ?? null })
                  }
                  disabled={!draft.is_blocked}
                  rows={3}
                  className="w-full rounded-md border border-neutral-200 px-3 py-2 text-sm outline-none focus:border-neutral-400 disabled:bg-neutral-50 disabled:text-neutral-400"
                />
              </label>

              <label className="block">
                <div className="mb-1 text-[12px] text-neutral-500">Parent issue</div>
                <select
                  aria-label="Parent issue"
                  value={draft.parent_id ?? ""}
                  onChange={(event) =>
                    void enqueuePatch({
                      parent_id: event.target.value ? Number(event.target.value) : null,
                    })
                  }
                  className="w-full rounded-md border border-neutral-200 px-3 py-2 text-sm outline-none focus:border-neutral-400"
                >
                  <option value="">No parent</option>
                  {(subIssuesQuery.data?.items ?? [])
                    .filter((candidate) => candidate.id !== draft.id)
                    .map((candidate) => (
                      <option key={candidate.id} value={candidate.id}>
                        {candidate.key} - {candidate.title}
                      </option>
                    ))}
                </select>
              </label>

              <button
                type="button"
                onClick={() => setMoreOpen((current) => !current)}
                aria-label="More properties"
                className="flex w-full items-center justify-between rounded-md border border-neutral-200 px-3 py-2 text-sm text-neutral-700"
              >
                <span>More properties</span>
                <ChevronDown className={cn("h-4 w-4 transition-transform", moreOpen && "rotate-180")} />
              </button>

              {moreOpen ? (
                <div className="space-y-4 border-t border-neutral-200 pt-4">
                  <PropertyRow label="Quarter" value={draft.quarter} />
                  <PropertyRow label="Risk level" value={draft.risk_level} />
                  <PropertyRow label="Customer impact" value={draft.customer_impact} />
                  <PropertyRow label="SLA" value={`${draft.sla_hours}h`} />
                  <PropertyRow label="Actual hours" value={`${draft.actual_hours}h`} />
                  <PropertyRow label="Progress" value={`${draft.progress_percentage}%`} />
                  <PropertyRow label="Department" value={draft.department || "—"} />
                  <PropertyRow label="Team" value={draft.team || "—"} />
                </div>
              ) : null}
            </div>
          </aside>
        </div>

        {showDeleteDialog ? (
          <div className="absolute inset-0 z-20 flex items-center justify-center bg-neutral-950/40 p-4">
            <div className="w-full max-w-sm rounded-lg border border-neutral-200 bg-white p-5 shadow-sm">
              <div className="text-base font-semibold text-neutral-950">Delete issue?</div>
              <div className="mt-2 text-sm text-neutral-600">
                {draft.key} will be removed from active views.
              </div>
              <div className="mt-5 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowDeleteDialog(false)}
                  className="rounded-md border border-neutral-200 px-3 py-2 text-sm text-neutral-700 hover:bg-neutral-50"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => deleteMutation.mutate()}
                  className="rounded-md bg-red-600 px-3 py-2 text-sm text-white hover:bg-red-700"
                >
                  {deleteMutation.isPending ? "Deleting..." : "Delete"}
                </button>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    );
  })();

  if (mode === "sheet") {
    return (
      <div className="fixed inset-0 z-40 flex justify-end bg-neutral-950/20">
        <button
          type="button"
          onClick={onClose}
          className="h-full flex-1 cursor-default"
          aria-label="Close issue backdrop"
        />
        <section className="relative h-full w-full max-w-[840px] border-l border-neutral-200 bg-white shadow-sm">
          {panelBody}
        </section>
      </div>
    );
  }

  return <div className="mx-auto w-full max-w-6xl rounded-lg border border-neutral-200 bg-white">{panelBody}</div>;
}

function PropertyRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3 text-sm">
      <div className="text-neutral-500">{label}</div>
      <div className="text-right text-neutral-800">{value}</div>
    </div>
  );
}
