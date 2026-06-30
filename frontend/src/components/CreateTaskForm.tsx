import { forwardRef, useEffect, useImperativeHandle, useState } from "react";
import { metaApi } from "../api/meta";
import type { TaskCreate, TaskPriority, TaskStatus, Quarter, RiskLevel, CustomerImpact } from "../types/task";
import type { Department, Team, ProjectMeta, UserMeta } from "../types/meta";

const STATUSES: TaskStatus[] = ["Todo", "In Progress", "Review", "Done"];
const PRIORITIES: TaskPriority[] = ["Low", "Medium", "High", "Critical"];
const QUARTERS: Quarter[] = ["Q1", "Q2", "Q3", "Q4"];
const RISK_LEVELS: RiskLevel[] = ["Low", "Medium", "High"];
const CUSTOMER_IMPACTS: CustomerImpact[] = ["None", "Low", "Medium", "High", "Internal"];
const STORY_POINTS = [1, 2, 3, 5, 8, 13];
const SLA_HOURS = [24, 48, 72, 120];
const TODAY = new Date().toISOString().split("T")[0];

interface Props {
  readonly onCreate: (data: TaskCreate, projectId: number) => Promise<unknown>;
  readonly currentProjectId?: number | null;
  readonly initialStatus?: TaskStatus;
}

export interface CreateTaskFormHandle {
  open: () => void;
}

interface FormState {
  title: string;
  description: string;
  status: TaskStatus;
  priority: TaskPriority;
  due_date: string;
  story_points: number;
  estimated_hours: number;
  quarter: Quarter;
  risk_level: RiskLevel;
  customer_impact: CustomerImpact;
  sla_hours: number;
  tagsInput: string;
}

const INITIAL: FormState = {
  title: "",
  description: "",
  status: "Todo",
  priority: "Medium",
  due_date: TODAY,
  story_points: 3,
  estimated_hours: 8,
  quarter: "Q1",
  risk_level: "Low",
  customer_impact: "None",
  sla_hours: 48,
  tagsInput: "",
};

function createInitialState(initialStatus: TaskStatus): FormState {
  return {
    ...INITIAL,
    status: initialStatus,
  };
}

export const CreateTaskForm = forwardRef<CreateTaskFormHandle, Props>(function CreateTaskForm(
  {
    onCreate,
    currentProjectId,
    initialStatus = "Todo",
  },
  ref,
) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<FormState>(() => createInitialState(initialStatus));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Cascading dropdown lists
  const [departments, setDepartments] = useState<Department[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [projects, setProjects] = useState<ProjectMeta[]>([]);
  const [assignees, setAssignees] = useState<UserMeta[]>([]);

  // Selected IDs
  const [depId, setDepId] = useState<number | "">("");
  const [teamId, setTeamId] = useState<number | "">("");
  const [projId, setProjId] = useState<number | "">("");
  const [assigneeId, setAssigneeId] = useState<number | "">("");

  // Fetch departments when form opens
  useEffect(() => {
    if (open) {
      metaApi.getDepartments().then(setDepartments).catch(console.error);
    }
  }, [open]);

  useImperativeHandle(ref, () => ({
    open: () => {
      setError("");
      setForm(createInitialState(initialStatus));
      setOpen(true);
    },
  }), [initialStatus]);

  // If a project is selected globally, load and pre-select its cascade
  useEffect(() => {
    if (open && currentProjectId) {
      setProjId(currentProjectId);
      metaApi.getUsers(currentProjectId).then(setAssignees).catch(console.error);
    }
  }, [open, currentProjectId]);

  // When Department changes, load Teams
  const handleDepartmentChange = async (dId: number | "") => {
    setDepId(dId);
    setTeamId("");
    setProjId("");
    setAssigneeId("");
    setTeams([]);
    setProjects([]);
    setAssignees([]);

    if (dId !== "") {
      try {
        const data = await metaApi.getTeams(dId);
        setTeams(data);
      } catch (err) {
        console.error("Gagal memuat teams", err);
      }
    }
  };

  // When Team changes, load Projects
  const handleTeamChange = async (tId: number | "") => {
    setTeamId(tId);
    setProjId("");
    setAssigneeId("");
    setProjects([]);
    setAssignees([]);

    if (tId !== "") {
      try {
        const data = await metaApi.getProjects(tId);
        setProjects(data);
      } catch (err) {
        console.error("Gagal memuat projects", err);
      }
    }
  };

  // When Project changes, load Users/Members
  const handleProjectChange = async (pId: number | "") => {
    setProjId(pId);
    setAssigneeId("");
    setAssignees([]);

    if (pId !== "") {
      try {
        const data = await metaApi.getUsers(pId);
        setAssignees(data);
      } catch (err) {
        console.error("Gagal memuat users", err);
      }
    }
  };

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = async () => {
    if (!form.title.trim()) {
      setError("Judul task wajib diisi");
      return;
    }
    if (!projId) {
      setError("Proyek wajib dipilih");
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
      assignee_id: assigneeId ? Number(assigneeId) : null,
      due_date: form.due_date,
      story_points: form.story_points,
      estimated_hours: form.estimated_hours,
      quarter: form.quarter,
      risk_level: form.risk_level,
      customer_impact: form.customer_impact,
      sla_hours: form.sla_hours,
      tags,
    };

    setLoading(true);
    setError("");
    try {
      await onCreate(payload, Number(projId));
      setForm(createInitialState(initialStatus));
      setDepId("");
      setTeamId("");
      setProjId("");
      setAssigneeId("");
      setOpen(false);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Gagal membuat task. Coba lagi.");
    } finally {
      setLoading(false);
    }
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="w-full border-2 border-dashed border-slate-200 rounded-xl py-3 text-sm text-slate-400 hover:border-blue-300 hover:text-blue-400 hover:bg-blue-50/55 transition-all duration-200 font-medium cursor-pointer"
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
            onClick={() => {
              setOpen(false);
              setError("");
              setForm(createInitialState(initialStatus));
              setDepId("");
              setTeamId("");
              setProjId("");
              setAssigneeId("");
            }}
            className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
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
            <label htmlFor="create-title" className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">
              Judul Task *
            </label>
            <input
              id="create-title"
              value={form.title}
              onChange={(e) => {
                set("title", e.target.value);
                setError("");
              }}
              placeholder="Judul task... *"
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              autoFocus
              onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
            />
          </div>

          {/* Description */}
          <div>
            <label htmlFor="create-description" className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">
              Deskripsi
            </label>
            <textarea
              id="create-description"
              value={form.description}
              onChange={(e) => set("description", e.target.value)}
              placeholder="Deskripsi (opsional)..."
              rows={2}
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 resize-none"
            />
          </div>

          {/* Cascading selectors section */}
          <div className="border border-slate-100 rounded-xl p-4 bg-slate-50/50 space-y-3">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wide block">
              Workspace & Assignee
            </span>
            <div className="grid grid-cols-2 gap-3">
              {/* Department */}
              <div>
                <label htmlFor="create-department-select" className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                  Departemen
                </label>
                <select
                  id="create-department-select"
                  value={depId}
                  onChange={(e) => handleDepartmentChange(e.target.value ? Number(e.target.value) : "")}
                  className="w-full border border-slate-200 rounded-lg px-3 py-1.5 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
                >
                  <option value="">-- Pilih Departemen --</option>
                  {departments.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Team */}
              <div>
                <label htmlFor="create-team-select" className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                  Tim
                </label>
                <select
                  id="create-team-select"
                  value={teamId}
                  onChange={(e) => handleTeamChange(e.target.value ? Number(e.target.value) : "")}
                  disabled={!depId}
                  className="w-full border border-slate-200 rounded-lg px-3 py-1.5 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:bg-slate-100 disabled:text-slate-400"
                >
                  <option value="">-- Pilih Tim --</option>
                  {teams.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Project */}
              <div>
                <label htmlFor="create-project-select" className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                  Proyek *
                </label>
                <select
                  id="create-project-select"
                  value={projId}
                  onChange={(e) => handleProjectChange(e.target.value ? Number(e.target.value) : "")}
                  disabled={!teamId && !currentProjectId}
                  className="w-full border border-slate-200 rounded-lg px-3 py-1.5 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:bg-slate-100 disabled:text-slate-400"
                >
                  <option value="">-- Pilih Proyek --</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.key})
                    </option>
                  ))}
                  {currentProjectId && !projects.some((p) => p.id === currentProjectId) && (
                    <option value={currentProjectId}>Proyek Aktif (ID: {currentProjectId})</option>
                  )}
                </select>
              </div>

              {/* Assignee */}
              <div>
                <label htmlFor="create-assignee-select" className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                  Assignee
                </label>
                <select
                  id="create-assignee-select"
                  value={assigneeId}
                  onChange={(e) => setAssigneeId(e.target.value ? Number(e.target.value) : "")}
                  disabled={!projId}
                  className="w-full border border-slate-200 rounded-lg px-3 py-1.5 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:bg-slate-100 disabled:text-slate-400"
                >
                  <option value="">-- Pilih Assignee --</option>
                  {assignees.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.full_name} ({u.email})
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Status + Priority */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="create-status" className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">
                Status
              </label>
              <select
                id="create-status"
                value={form.status}
                onChange={(e) => set("status", e.target.value as TaskStatus)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
              >
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="create-priority" className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">
                Priority
              </label>
              <select
                id="create-priority"
                value={form.priority}
                onChange={(e) => set("priority", e.target.value as TaskPriority)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
              >
                {PRIORITIES.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Due Date + Story Points + Estimated Hours */}
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label htmlFor="create-due-date" className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">
                Due Date
              </label>
              <input
                id="create-due-date"
                type="date"
                value={form.due_date}
                onChange={(e) => set("due_date", e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
            </div>
            <div>
              <label htmlFor="create-story-points" className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">
                Story Points
              </label>
              <select
                id="create-story-points"
                value={form.story_points}
                onChange={(e) => set("story_points", Number(e.target.value))}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
              >
                {STORY_POINTS.map((sp) => (
                  <option key={sp} value={sp}>
                    {sp}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="create-estimated-hours" className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">
                Est. Hours
              </label>
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
              <label htmlFor="create-quarter" className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">
                Quarter
              </label>
              <select
                id="create-quarter"
                value={form.quarter}
                onChange={(e) => set("quarter", e.target.value as Quarter)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
              >
                {QUARTERS.map((q) => (
                  <option key={q} value={q}>
                    {q}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="create-risk-level" className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">
                Risk Level
              </label>
              <select
                id="create-risk-level"
                value={form.risk_level}
                onChange={(e) => set("risk_level", e.target.value as RiskLevel)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
              >
                {RISK_LEVELS.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="create-customer-impact" className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">
                Impact
              </label>
              <select
                id="create-customer-impact"
                value={form.customer_impact}
                onChange={(e) => set("customer_impact", e.target.value as CustomerImpact)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
              >
                {CUSTOMER_IMPACTS.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* SLA Hours + Tags */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="create-sla-hours" className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">
                SLA Hours
              </label>
              <select
                id="create-sla-hours"
                value={form.sla_hours}
                onChange={(e) => set("sla_hours", Number(e.target.value))}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
              >
                {SLA_HOURS.map((h) => (
                  <option key={h} value={h}>
                    {h}h
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="create-tags" className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">
                Tags
              </label>
              <input
                id="create-tags"
                value={form.tagsInput}
                onChange={(e) => set("tagsInput", e.target.value)}
                placeholder="security, automation"
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
              id="create-cancel"
              onClick={() => {
                setOpen(false);
                setError("");
                setForm(createInitialState(initialStatus));
                setDepId("");
                setTeamId("");
                setProjId("");
                setAssigneeId("");
              }}
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
});
