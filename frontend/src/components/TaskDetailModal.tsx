import { useState, useEffect } from "react";
import { metaApi } from "../api/meta";
import type { Task, TaskStatus, TaskPriority, Quarter, RiskLevel, CustomerImpact } from "../types/task";
import type { UserMeta } from "../types/meta";

interface Props {
  readonly task: Task;
  readonly onUpdate: (id: number, data: any) => Promise<any>;
  readonly onDelete: (id: number) => Promise<void>;
  readonly onClose: () => void;
}

const STATUSES: TaskStatus[] = ["Todo", "In Progress", "Review", "Blocked", "Done"];
const PRIORITIES: TaskPriority[] = ["Low", "Medium", "High", "Critical"];
const QUARTERS: Quarter[] = ["Q1", "Q2", "Q3", "Q4"];
const RISK_LEVELS: RiskLevel[] = ["Low", "Medium", "High"];
const CUSTOMER_IMPACTS: CustomerImpact[] = ["None", "Low", "Medium", "High", "Internal"];
const STORY_POINTS = [1, 2, 3, 5, 8, 13];
const SLA_HOURS = [24, 48, 72, 120];

export function TaskDetailModal({ task, onUpdate, onDelete, onClose }: Props) {
  const [form, setForm] = useState({
    title: task.title,
    description: task.description,
    status: task.status,
    priority: task.priority,
    due_date: task.due_date,
    story_points: task.story_points,
    estimated_hours: task.estimated_hours,
    actual_hours: task.actual_hours,
    progress_percentage: task.progress_percentage,
    quarter: task.quarter,
    risk_level: task.risk_level,
    customer_impact: task.customer_impact,
    sla_hours: task.sla_hours,
    tagsInput: task.tags.join(", "),
  });

  const [assigneeId, setAssigneeId] = useState<number | "">(task.assignee_id || "");
  const [projectMembers, setProjectMembers] = useState<UserMeta[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  // Load project members on mount
  useEffect(() => {
    metaApi.getUsers(task.project_id)
      .then(setProjectMembers)
      .catch(console.error);
  }, [task.project_id]);

  const handleChange = (field: string, val: any) => {
    setForm((prev) => ({ ...prev, [field]: val }));
  };

  const handleSave = async () => {
    if (!form.title.trim()) {
      setError("Judul task tidak boleh kosong.");
      return;
    }

    setSaving(true);
    setError("");

    const tags = form.tagsInput
      .split(",")
      .map((t) => t.trim())
      .filter((t) => t !== "");

    const payload = {
      title: form.title,
      description: form.description,
      status: form.status,
      priority: form.priority,
      assignee_id: assigneeId ? Number(assigneeId) : null,
      due_date: form.due_date,
      story_points: form.story_points,
      estimated_hours: form.estimated_hours,
      actual_hours: form.actual_hours,
      progress_percentage: form.progress_percentage,
      quarter: form.quarter,
      risk_level: form.risk_level,
      customer_impact: form.customer_impact,
      sla_hours: form.sla_hours,
      tags,
    };

    try {
      await onUpdate(task.id, payload);
      onClose();
    } catch (err: any) {
      console.error(err);
      setError("Gagal menyimpan perubahan. Coba lagi.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm(`Hapus task "WDD-${task.id}: ${task.title}"?`)) return;
    setSaving(true);
    try {
      await onDelete(task.id);
      onClose();
    } catch (err) {
      console.error(err);
      setError("Gagal menghapus task.");
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-900/60 z-50 flex items-center justify-center p-4 backdrop-blur-sm animate-fade-in">
      <div className="bg-white rounded-xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl border border-slate-100 animate-slide-up">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/50">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold bg-blue-100 text-blue-800 px-2.5 py-1 rounded">
              WDD-{task.id}
            </span>
            <span className="text-slate-400 text-xs">
              Dibuat pada {new Date(task.created_at).toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" })}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleDelete}
              disabled={saving}
              className="text-xs font-medium text-red-600 hover:text-red-700 bg-red-50 hover:bg-red-100 px-3 py-1.5 rounded-lg transition-colors cursor-pointer"
            >
              Hapus Task
            </button>
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Main Details (Left side) */}
          <div className="md:col-span-2 space-y-4">
            <div>
              <label htmlFor="detail-title" className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Judul Task</label>
              <input
                id="detail-title"
                type="text"
                value={form.title}
                onChange={(e) => handleChange("title", e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-base font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
            </div>

            <div>
              <label htmlFor="detail-description" className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Deskripsi</label>
              <textarea
                id="detail-description"
                rows={5}
                value={form.description}
                onChange={(e) => handleChange("description", e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-400 resize-none leading-relaxed"
                placeholder="Tambahkan deskripsi detail..."
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Department</label>
                <div className="w-full bg-slate-50 border border-slate-250 rounded-lg px-3 py-2 text-sm text-slate-500 font-semibold select-none">
                  {task.department || "No Department"}
                </div>
              </div>
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Team</label>
                <div className="w-full bg-slate-50 border border-slate-250 rounded-lg px-3 py-2 text-sm text-slate-500 font-semibold select-none">
                  {task.team || "No Team"}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="detail-tags" className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Tags</label>
                <input
                  id="detail-tags"
                  type="text"
                  value={form.tagsInput}
                  onChange={(e) => handleChange("tagsInput", e.target.value)}
                  placeholder="backend, api, bug"
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Sprint</label>
                <div className="w-full bg-slate-50 border border-slate-250 rounded-lg px-3 py-2 text-sm text-slate-500 font-semibold select-none">
                  {task.sprint || "No Sprint"}
                </div>
              </div>
            </div>

            {/* Readonly stats */}
            <div className="bg-slate-50 rounded-xl p-4 grid grid-cols-3 gap-4 text-center border border-slate-100">
              <div>
                <span className="text-xs text-slate-400 block mb-0.5">Attachments</span>
                <span className="font-semibold text-slate-700 text-sm">📎 {task.attachments_count}</span>
              </div>
              <div>
                <span className="text-xs text-slate-400 block mb-0.5">Comments</span>
                <span className="font-semibold text-slate-700 text-sm">💬 {task.comments_count}</span>
              </div>
              <div>
                <span className="text-xs text-slate-400 block mb-0.5">Watchers</span>
                <span className="font-semibold text-slate-700 text-sm">👁️ {task.watchers_count}</span>
              </div>
            </div>
          </div>

          {/* Sidebar Metadata (Right side) */}
          <div className="bg-slate-50/50 border border-slate-100 rounded-xl p-4 space-y-4">
            <div>
              <label htmlFor="detail-status" className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Status</label>
              <select
                id="detail-status"
                value={form.status}
                onChange={(e) => handleChange("status", e.target.value as TaskStatus)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
              >
                {STATUSES.map((st) => (
                  <option key={st} value={st}>{st === "Review" ? "In Review" : st}</option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="detail-priority" className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Priority</label>
              <select
                id="detail-priority"
                value={form.priority}
                onChange={(e) => handleChange("priority", e.target.value as TaskPriority)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
              >
                {PRIORITIES.map((pr) => (
                  <option key={pr} value={pr}>{pr}</option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="detail-assignee-select" className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Assignee</label>
              <select
                id="detail-assignee-select"
                value={assigneeId}
                onChange={(e) => setAssigneeId(e.target.value ? Number(e.target.value) : "")}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
              >
                <option value="">Unassigned</option>
                {projectMembers.map((m) => (
                  <option key={m.id} value={m.id}>{m.full_name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Created By</label>
              <div className="w-full bg-slate-100 border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-500 font-semibold select-none">
                {task.created_by}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label htmlFor="detail-story-points" className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Story Points</label>
                <select
                  id="detail-story-points"
                  value={form.story_points}
                  onChange={(e) => handleChange("story_points", Number(e.target.value))}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
                >
                  {STORY_POINTS.map((sp) => (
                    <option key={sp} value={sp}>{sp}</option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="detail-estimated-hours" className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Est. Hours</label>
                <input
                  id="detail-estimated-hours"
                  type="number"
                  min={1}
                  value={form.estimated_hours}
                  onChange={(e) => handleChange("estimated_hours", Number(e.target.value))}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label htmlFor="detail-actual-hours" className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Act. Hours</label>
                <input
                  id="detail-actual-hours"
                  type="number"
                  min={0}
                  value={form.actual_hours}
                  onChange={(e) => handleChange("actual_hours", Number(e.target.value))}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>

              <div>
                <label htmlFor="detail-progress" className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Progress (%)</label>
                <input
                  id="detail-progress"
                  type="number"
                  min={0}
                  max={100}
                  value={form.progress_percentage}
                  onChange={(e) => handleChange("progress_percentage", Number(e.target.value))}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label htmlFor="detail-quarter" className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Quarter</label>
                <select
                  id="detail-quarter"
                  value={form.quarter}
                  onChange={(e) => handleChange("quarter", e.target.value as Quarter)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
                >
                  {QUARTERS.map((q) => (
                    <option key={q} value={q}>{q}</option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="detail-risk-level" className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Risk Level</label>
                <select
                  id="detail-risk-level"
                  value={form.risk_level}
                  onChange={(e) => handleChange("risk_level", e.target.value as RiskLevel)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
                >
                  {RISK_LEVELS.map((r) => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label htmlFor="detail-impact" className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Impact</label>
                <select
                  id="detail-impact"
                  value={form.customer_impact}
                  onChange={(e) => handleChange("customer_impact", e.target.value as CustomerImpact)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
                >
                  {CUSTOMER_IMPACTS.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="detail-sla-hours" className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">SLA Hours</label>
                <select
                  id="detail-sla-hours"
                  value={form.sla_hours}
                  onChange={(e) => handleChange("sla_hours", Number(e.target.value))}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
                >
                  {SLA_HOURS.map((h) => (
                    <option key={h} value={h}>{h}h</option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label htmlFor="detail-due-date" className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Due Date</label>
              <input
                id="detail-due-date"
                type="date"
                value={form.due_date}
                onChange={(e) => handleChange("due_date", e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-100 flex items-center justify-between bg-slate-50/50">
          <div className="text-xs text-red-500 font-medium">{error}</div>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              disabled={saving}
              className="text-sm font-medium text-slate-650 hover:text-slate-800 bg-white hover:bg-slate-55 border border-slate-200 px-4 py-2 rounded-lg transition-colors cursor-pointer"
            >
              Batal
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="text-sm font-medium text-white bg-blue-650 hover:bg-blue-700 disabled:bg-blue-300 px-4 py-2 rounded-lg transition-colors cursor-pointer"
            >
              {saving ? "Menyimpan..." : "Simpan Perubahan"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
