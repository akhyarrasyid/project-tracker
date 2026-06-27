import { useState } from "react";
import type { Task, TaskStatus, TaskPriority, Quarter, RiskLevel, CustomerImpact } from "../types/task";

interface Props {
  task: Task;
  onUpdate: (id: number, data: any) => Promise<any>;
  onDelete: (id: number) => Promise<void>;
  onClose: () => void;
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
    department: task.department,
    team: task.team,
    assignee: task.assignee,
    created_by: task.created_by,
    due_date: task.due_date,
    story_points: task.story_points,
    estimated_hours: task.estimated_hours,
    actual_hours: task.actual_hours,
    progress_percentage: task.progress_percentage,
    sprint: task.sprint,
    quarter: task.quarter,
    risk_level: task.risk_level,
    customer_impact: task.customer_impact,
    sla_hours: task.sla_hours,
    tagsInput: task.tags.join(", "),
  });

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleChange = (field: string, val: any) => {
    setForm((prev) => ({ ...prev, [field]: val }));
  };

  const handleSave = async () => {
    if (!form.title.trim()) {
      setError("Judul task tidak boleh kosong.");
      return;
    }
    if (!form.department.trim() || !form.team.trim() || !form.assignee.trim() || !form.created_by.trim()) {
      setError("Department, team, assignee, dan created by wajib diisi.");
      return;
    }
    if (!form.sprint.trim()) {
      setError("Sprint wajib diisi.");
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
      department: form.department,
      team: form.team,
      assignee: form.assignee,
      created_by: form.created_by,
      due_date: form.due_date,
      story_points: form.story_points,
      estimated_hours: form.estimated_hours,
      actual_hours: form.actual_hours,
      progress_percentage: form.progress_percentage,
      sprint: form.sprint,
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
    } catch {
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
              className="text-xs font-medium text-red-600 hover:text-red-700 bg-red-50 hover:bg-red-100 px-3 py-1.5 rounded-lg transition-colors"
            >
              Hapus Task
            </button>
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-100 transition-colors"
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
              <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Deskripsi</label>
              <textarea
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
                <input
                  type="text"
                  value={form.department}
                  onChange={(e) => handleChange("department", e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Team</label>
                <input
                  type="text"
                  value={form.team}
                  onChange={(e) => handleChange("team", e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Tags</label>
                <input
                  type="text"
                  value={form.tagsInput}
                  onChange={(e) => handleChange("tagsInput", e.target.value)}
                  placeholder="backend, api, bug"
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Sprint</label>
                <input
                  type="text"
                  value={form.sprint}
                  onChange={(e) => handleChange("sprint", e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
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
              <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Priority</label>
              <select
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
              <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Assignee</label>
              <input
                type="text"
                value={form.assignee}
                onChange={(e) => handleChange("assignee", e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
            </div>

            <div>
              <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Created By</label>
              <input
                type="text"
                value={form.created_by}
                onChange={(e) => handleChange("created_by", e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Story Points</label>
                <select
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
                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Est. Hours</label>
                <input
                  type="number"
                  value={form.estimated_hours}
                  onChange={(e) => handleChange("estimated_hours", Number(e.target.value))}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Actual Hours</label>
                <input
                  type="number"
                  value={form.actual_hours}
                  onChange={(e) => handleChange("actual_hours", Number(e.target.value))}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">SLA Hours</label>
                <select
                  value={form.sla_hours}
                  onChange={(e) => handleChange("sla_hours", Number(e.target.value))}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
                >
                  {SLA_HOURS.map((sla) => (
                    <option key={sla} value={sla}>{sla}h</option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Progress Percentage</label>
              <div className="flex items-center gap-2">
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={form.progress_percentage}
                  onChange={(e) => handleChange("progress_percentage", Number(e.target.value))}
                  className="flex-1 accent-blue-500"
                />
                <span className="text-xs font-semibold text-slate-600 w-8 text-right">{form.progress_percentage}%</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Quarter</label>
                <select
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
                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Risk Level</label>
                <select
                  value={form.risk_level}
                  onChange={(e) => handleChange("risk_level", e.target.value as RiskLevel)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
                >
                  {RISK_LEVELS.map((rl) => (
                    <option key={rl} value={rl}>{rl}</option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Customer Impact</label>
              <select
                value={form.customer_impact}
                onChange={(e) => handleChange("customer_impact", e.target.value as CustomerImpact)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
              >
                {CUSTOMER_IMPACTS.map((ci) => (
                  <option key={ci} value={ci}>{ci}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Due Date</label>
              <input
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
              className="text-sm font-medium text-slate-600 hover:text-slate-800 bg-white hover:bg-slate-100 border border-slate-200 px-4 py-2 rounded-lg transition-colors"
            >
              Batal
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
            >
              {saving ? "Menyimpan..." : "Simpan Perubahan"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
