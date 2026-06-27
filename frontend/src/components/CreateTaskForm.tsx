import { useState } from "react";
import type { TaskCreate, TaskPriority, TaskStatus, Quarter, RiskLevel, CustomerImpact } from "../types/task";

const STATUSES: TaskStatus[] = ["Todo", "In Progress", "Review", "Blocked", "Done"];
const PRIORITIES: TaskPriority[] = ["Low", "Medium", "High", "Critical"];
const QUARTERS: Quarter[] = ["Q1", "Q2", "Q3", "Q4"];
const RISK_LEVELS: RiskLevel[] = ["Low", "Medium", "High"];
const CUSTOMER_IMPACTS: CustomerImpact[] = ["None", "Low", "Medium", "High", "Internal"];
const STORY_POINTS = [1, 2, 3, 5, 8, 13];
const SLA_HOURS = [24, 48, 72, 120];
const TODAY = new Date().toISOString().split("T")[0];

interface Props {
  onCreate: (data: TaskCreate) => Promise<unknown>;
}

type FormState = Omit<TaskCreate, "tags"> & { tagsInput: string };

const INITIAL: FormState = {
  title: "",
  description: "",
  status: "Todo",
  priority: "Medium",
  department: "",
  team: "",
  assignee: "",
  created_by: "",
  due_date: TODAY,
  story_points: 3,
  estimated_hours: 8,
  sprint: "",
  quarter: "Q1",
  risk_level: "Low",
  customer_impact: "None",
  sla_hours: 48,
  tagsInput: "",
};

export function CreateTaskForm({ onCreate }: Props) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<FormState>(INITIAL);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = async () => {
    if (!form.title.trim()) {
      setError("Gagal membuat task. Coba lagi.");
      return;
    }
    if (!form.department.trim() || !form.team.trim() || !form.assignee.trim() || !form.created_by.trim()) {
      setError("Gagal membuat task. Coba lagi.");
      return;
    }
    if (!form.sprint.trim()) {
      setError("Gagal membuat task. Coba lagi.");
      return;
    }

    const tags = form.tagsInput
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean)
      .slice(0, 4);

    const payload: TaskCreate = {
      title: form.title.trim(),
      description: form.description.trim(),
      status: form.status,
      priority: form.priority,
      department: form.department.trim(),
      team: form.team.trim(),
      assignee: form.assignee.trim(),
      created_by: form.created_by.trim(),
      due_date: form.due_date,
      story_points: form.story_points,
      estimated_hours: form.estimated_hours,
      sprint: form.sprint.trim(),
      quarter: form.quarter,
      risk_level: form.risk_level,
      customer_impact: form.customer_impact,
      sla_hours: form.sla_hours,
      tags,
    };

    setLoading(true);
    setError("");
    try {
      await onCreate(payload);
      setForm(INITIAL);
      setOpen(false);
    } catch {
      setError("Gagal membuat task. Coba lagi.");
    } finally {
      setLoading(false);
    }
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="w-full border-2 border-dashed border-slate-200 rounded-xl py-3 text-sm text-slate-400 hover:border-blue-300 hover:text-blue-400 hover:bg-blue-50 transition-all duration-200 font-medium cursor-pointer"
      >
        + Tambah Task Baru
      </button>
    );
  }

  return (
    <div className="fixed inset-0 bg-slate-900/60 z-50 flex items-center justify-center p-4 backdrop-blur-sm animate-fade-in">
      <div className="bg-white rounded-xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl border border-slate-100 animate-slide-up">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/50">
          <h3 className="font-bold text-slate-800 text-lg">Buat Task Baru</h3>
          <button
            onClick={() => { setOpen(false); setError(""); setForm(INITIAL); }}
            className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Form Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {/* Title */}
          <div>
            <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Judul Task *</label>
            <input
              id="create-title"
              value={form.title}
              onChange={(e) => { set("title", e.target.value); setError(""); }}
              placeholder="Judul task... *"
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              autoFocus
              onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
            />
          </div>

          {/* Description */}
          <div>
            <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Deskripsi</label>
            <textarea
              id="create-description"
              value={form.description}
              onChange={(e) => set("description", e.target.value)}
              placeholder="Deskripsi (opsional)..."
              rows={3}
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 resize-none"
            />
          </div>

          {/* Status + Priority */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Status</label>
              <select
                id="create-status"
                value={form.status}
                onChange={(e) => set("status", e.target.value as TaskStatus)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
              >
                {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Priority</label>
              <select
                id="create-priority"
                value={form.priority}
                onChange={(e) => set("priority", e.target.value as TaskPriority)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
              >
                {PRIORITIES.map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
          </div>

          {/* Department + Team */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Department *</label>
              <input
                id="create-department"
                value={form.department}
                onChange={(e) => set("department", e.target.value)}
                placeholder="Department *"
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
            </div>
            <div>
              <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Team *</label>
              <input
                id="create-team"
                value={form.team}
                onChange={(e) => set("team", e.target.value)}
                placeholder="Team *"
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
            </div>
          </div>

          {/* Assignee + Created By */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Assignee *</label>
              <input
                id="create-assignee"
                value={form.assignee}
                onChange={(e) => set("assignee", e.target.value)}
                placeholder="Assignee *"
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
            </div>
            <div>
              <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Created By *</label>
              <input
                id="create-created-by"
                value={form.created_by}
                onChange={(e) => set("created_by", e.target.value)}
                placeholder="Created by *"
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
            </div>
          </div>

          {/* Due Date + Sprint */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Due Date</label>
              <input
                id="create-due-date"
                type="date"
                value={form.due_date}
                onChange={(e) => set("due_date", e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
            </div>
            <div>
              <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Sprint *</label>
              <input
                id="create-sprint"
                value={form.sprint}
                onChange={(e) => set("sprint", e.target.value)}
                placeholder="Sprint (e.g. Sprint-1) *"
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
            </div>
          </div>

          {/* Story Points + Estimated Hours */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Story Points</label>
              <select
                id="create-story-points"
                value={form.story_points}
                onChange={(e) => set("story_points", Number(e.target.value))}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
              >
                {STORY_POINTS.map((sp) => <option key={sp} value={sp}>{sp}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Estimated Hours</label>
              <input
                id="create-estimated-hours"
                type="number"
                min={1}
                value={form.estimated_hours}
                onChange={(e) => set("estimated_hours", Number(e.target.value))}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
            </div>
          </div>

          {/* Quarter + Risk Level + Customer Impact */}
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Quarter</label>
              <select
                id="create-quarter"
                value={form.quarter}
                onChange={(e) => set("quarter", e.target.value as Quarter)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
              >
                {QUARTERS.map((q) => <option key={q} value={q}>{q}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Risk Level</label>
              <select
                id="create-risk-level"
                value={form.risk_level}
                onChange={(e) => set("risk_level", e.target.value as RiskLevel)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
              >
                {RISK_LEVELS.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Impact</label>
              <select
                id="create-customer-impact"
                value={form.customer_impact}
                onChange={(e) => set("customer_impact", e.target.value as CustomerImpact)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
              >
                {CUSTOMER_IMPACTS.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
          </div>

          {/* SLA Hours */}
          <div>
            <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">SLA Hours</label>
            <select
              id="create-sla-hours"
              value={form.sla_hours}
              onChange={(e) => set("sla_hours", Number(e.target.value))}
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
            >
              {SLA_HOURS.map((h) => <option key={h} value={h}>{h}h</option>)}
            </select>
          </div>

          {/* Tags */}
          <div>
            <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Tags</label>
            <input
              id="create-tags"
              value={form.tagsInput}
              onChange={(e) => set("tagsInput", e.target.value)}
              placeholder="Tags (comma-separated, max 4): security, automation"
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-100 flex items-center justify-between bg-slate-50/50">
          <div className="text-xs text-red-500 font-medium">{error}</div>
          <div className="flex gap-2">
            <button
              id="create-cancel"
              onClick={() => { setOpen(false); setError(""); setForm(INITIAL); }}
              disabled={loading}
              className="text-sm font-medium text-slate-600 hover:text-slate-800 bg-white hover:bg-slate-100 border border-slate-200 px-4 py-2 rounded-lg transition-colors cursor-pointer"
            >
              Batal
            </button>
            <button
              id="create-submit"
              onClick={handleSubmit}
              disabled={loading}
              className="text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 px-4 py-2 rounded-lg transition-colors cursor-pointer"
            >
              {loading ? "Menyimpan..." : "Buat Task"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
