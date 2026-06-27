import { useState } from "react";
import type { TaskCreate, TaskPriority, TaskStatus, Quarter, RiskLevel, CustomerImpact } from "../types/task";

// ── Static option sets ───────────────────────────────────────────────────────

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
      setError("Judul tidak boleh kosong.");
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
        className="w-full border-2 border-dashed border-slate-200 rounded-xl py-3 text-sm text-slate-400 hover:border-blue-300 hover:text-blue-400 hover:bg-blue-50 transition-all duration-200 font-medium"
      >
        + Tambah Task Baru
      </button>
    );
  }

  return (
    <div className="bg-white rounded-xl border-2 border-blue-200 p-4 shadow-sm space-y-3 text-sm">
      <h3 className="font-semibold text-slate-700">Task Baru</h3>

      {/* Title */}
      <input
        id="create-title"
        value={form.title}
        onChange={(e) => { set("title", e.target.value); setError(""); }}
        placeholder="Judul task... *"
        className="w-full border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
        autoFocus
        onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
      />

      {/* Description */}
      <textarea
        id="create-description"
        value={form.description}
        onChange={(e) => set("description", e.target.value)}
        placeholder="Deskripsi (opsional)..."
        rows={2}
        className="w-full border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400 resize-none"
      />

      {/* Status + Priority */}
      <div className="grid grid-cols-2 gap-2">
        <select
          id="create-status"
          value={form.status}
          onChange={(e) => set("status", e.target.value as TaskStatus)}
          className="border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
        >
          {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select
          id="create-priority"
          value={form.priority}
          onChange={(e) => set("priority", e.target.value as TaskPriority)}
          className="border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
        >
          {PRIORITIES.map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
      </div>

      {/* Department + Team */}
      <div className="grid grid-cols-2 gap-2">
        <input
          id="create-department"
          value={form.department}
          onChange={(e) => set("department", e.target.value)}
          placeholder="Department *"
          className="border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
        <input
          id="create-team"
          value={form.team}
          onChange={(e) => set("team", e.target.value)}
          placeholder="Team *"
          className="border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
      </div>

      {/* Assignee + Created By */}
      <div className="grid grid-cols-2 gap-2">
        <input
          id="create-assignee"
          value={form.assignee}
          onChange={(e) => set("assignee", e.target.value)}
          placeholder="Assignee *"
          className="border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
        <input
          id="create-created-by"
          value={form.created_by}
          onChange={(e) => set("created_by", e.target.value)}
          placeholder="Created by *"
          className="border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
      </div>

      {/* Due Date + Sprint */}
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-xs text-slate-400 mb-1 block">Due Date</label>
          <input
            id="create-due-date"
            type="date"
            value={form.due_date}
            onChange={(e) => set("due_date", e.target.value)}
            className="w-full border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </div>
        <input
          id="create-sprint"
          value={form.sprint}
          onChange={(e) => set("sprint", e.target.value)}
          placeholder="Sprint (e.g. Sprint-1) *"
          className="border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
      </div>

      {/* Story Points + Estimated Hours */}
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-xs text-slate-400 mb-1 block">Story Points</label>
          <select
            id="create-story-points"
            value={form.story_points}
            onChange={(e) => set("story_points", Number(e.target.value))}
            className="w-full border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
          >
            {STORY_POINTS.map((sp) => <option key={sp} value={sp}>{sp}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-slate-400 mb-1 block">Est. Hours</label>
          <input
            id="create-estimated-hours"
            type="number"
            min={1}
            value={form.estimated_hours}
            onChange={(e) => set("estimated_hours", Number(e.target.value))}
            className="w-full border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </div>
      </div>

      {/* Quarter + Risk Level + Customer Impact */}
      <div className="grid grid-cols-3 gap-2">
        <select
          id="create-quarter"
          value={form.quarter}
          onChange={(e) => set("quarter", e.target.value as Quarter)}
          className="border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
        >
          {QUARTERS.map((q) => <option key={q} value={q}>{q}</option>)}
        </select>
        <select
          id="create-risk-level"
          value={form.risk_level}
          onChange={(e) => set("risk_level", e.target.value as RiskLevel)}
          className="border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
        >
          {RISK_LEVELS.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
        <select
          id="create-customer-impact"
          value={form.customer_impact}
          onChange={(e) => set("customer_impact", e.target.value as CustomerImpact)}
          className="border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
        >
          {CUSTOMER_IMPACTS.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      {/* SLA Hours */}
      <div>
        <label className="text-xs text-slate-400 mb-1 block">SLA Hours</label>
        <select
          id="create-sla-hours"
          value={form.sla_hours}
          onChange={(e) => set("sla_hours", Number(e.target.value))}
          className="w-full border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
        >
          {SLA_HOURS.map((h) => <option key={h} value={h}>{h}h</option>)}
        </select>
      </div>

      {/* Tags */}
      <input
        id="create-tags"
        value={form.tagsInput}
        onChange={(e) => set("tagsInput", e.target.value)}
        placeholder="Tags (comma-separated, max 4): security, automation"
        className="w-full border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
      />

      {error && <p className="text-xs text-red-500">{error}</p>}

      <div className="flex gap-2">
        <button
          id="create-submit"
          onClick={handleSubmit}
          disabled={loading}
          className="flex-1 bg-blue-500 text-white rounded-lg py-2 hover:bg-blue-600 disabled:opacity-50 transition-colors font-medium"
        >
          {loading ? "Menyimpan..." : "Buat Task"}
        </button>
        <button
          id="create-cancel"
          onClick={() => { setOpen(false); setError(""); setForm(INITIAL); }}
          className="flex-1 bg-slate-100 text-slate-600 rounded-lg py-2 hover:bg-slate-200 transition-colors"
        >
          Batal
        </button>
      </div>
    </div>
  );
}
