/**
 * Domain types mirroring the backend Task model — all 26 fields.
 * Enums are kept as literal string unions so the frontend remains
 * independent of any backend enum library.
 */

// ── Enums ───────────────────────────────────────────────────────────────────

export type TaskStatus = "Todo" | "In Progress" | "Review" | "Blocked" | "Done";
export type TaskPriority = "Low" | "Medium" | "High" | "Critical";
export type Quarter = "Q1" | "Q2" | "Q3" | "Q4";
export type RiskLevel = "Low" | "Medium" | "High";
export type CustomerImpact = "None" | "Low" | "Medium" | "High" | "Internal";

// ── Full Task entity (API response) ─────────────────────────────────────────

export interface Task {
  id: number;
  title: string;
  description: string;
  status: TaskStatus;
  priority: TaskPriority;
  department: string;
  team: string;
  assignee: string;
  created_by: string;
  created_at: string;
  updated_at: string;
  due_date: string;
  completed_at: string | null;
  story_points: number;
  estimated_hours: number;
  actual_hours: number;
  progress_percentage: number;
  attachments_count: number;
  comments_count: number;
  watchers_count: number;
  sprint: string;
  quarter: Quarter;
  risk_level: RiskLevel;
  customer_impact: CustomerImpact;
  sla_hours: number;
  dependencies: number[];
  tags: string[];
}

// ── Create payload (all required fields from API) ────────────────────────────

export interface TaskCreate {
  title: string;
  description: string;
  status: TaskStatus;
  priority: TaskPriority;
  department: string;
  team: string;
  assignee: string;
  created_by: string;
  due_date: string;
  story_points: number;
  estimated_hours: number;
  sprint: string;
  quarter: Quarter;
  risk_level: RiskLevel;
  customer_impact: CustomerImpact;
  sla_hours: number;
  tags: string[];
}

// ── Update payload (all fields optional) ────────────────────────────────────

export interface TaskUpdate {
  title?: string;
  description?: string;
  status?: TaskStatus;
  priority?: TaskPriority;
  department?: string;
  team?: string;
  assignee?: string;
  due_date?: string;
  story_points?: number;
  estimated_hours?: number;
  actual_hours?: number;
  progress_percentage?: number;
  sprint?: string;
  quarter?: Quarter;
  risk_level?: RiskLevel;
  customer_impact?: CustomerImpact;
  sla_hours?: number;
  tags?: string[];
}

// ── Paginated API response envelope ─────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export type TaskListResponse = PaginatedResponse<Task>;
