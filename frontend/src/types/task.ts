/**
 * Domain types mirroring the backend Task model — all 26 fields.
 * Enums are kept as literal string unions so the frontend remains
 * independent of any backend enum library.
 */

// ── Enums ───────────────────────────────────────────────────────────────────

export type TaskStatus = "Todo" | "In Progress" | "Review" | "Done";
export type TaskPriority = "Low" | "Medium" | "High" | "Critical";
export type Quarter = "Q1" | "Q2" | "Q3" | "Q4";
export type RiskLevel = "Low" | "Medium" | "High";
export type CustomerImpact = "None" | "Low" | "Medium" | "High" | "Internal";

// ── Full Task entity (API response) ─────────────────────────────────────────

export interface Task {
  id: number;
  number: number;
  rank: number;
  version: number;
  key: string;
  project_key?: string | null;
  project_id?: number;
  sprint_id?: number | null;
  epic_id?: number | null;
  assignee_id?: number | null;
  parent_id?: number | null;
  title: string;
  description: string;
  status: TaskStatus;
  is_blocked: boolean;
  blocked_reason?: string | null;
  priority: TaskPriority;
  department?: string | null;
  team?: string | null;
  assignee?: string | null;
  created_by?: string | null;
  created_by_id?: number;
  created_at: string;
  updated_at: string;
  due_date: string;
  completed_at: string | null;
  completed_by_id?: number | null;
  story_points: number;
  estimated_hours: number;
  actual_hours: number;
  progress_percentage: number;
  attachments_count: number;
  comments_count: number;
  watchers_count: number;
  sprint?: string | null;
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
  is_blocked?: boolean;
  blocked_reason?: string | null;
  priority: TaskPriority;
  assignee_id?: number | null;
  parent_id?: number | null;
  sprint_id?: number | null;
  epic_id?: number | null;
  due_date: string;
  story_points: number;
  estimated_hours: number;
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
  is_blocked?: boolean;
  blocked_reason?: string | null;
  priority?: TaskPriority;
  assignee_id?: number | null;
  parent_id?: number | null;
  sprint_id?: number | null;
  epic_id?: number | null;
  due_date?: string;
  story_points?: number;
  estimated_hours?: number;
  actual_hours?: number;
  progress_percentage?: number;
  quarter?: Quarter;
  risk_level?: RiskLevel;
  customer_impact?: CustomerImpact;
  sla_hours?: number;
  tags?: string[];
}

export interface BoardColumn {
  status: TaskStatus;
  items: Task[];
  total_count: number;
  next_after?: number | null;
  next_before?: number | null;
}

export interface BoardResponse {
  columns: Record<TaskStatus, BoardColumn>;
}

export interface IssueMoveInput {
  status: TaskStatus;
  before_issue_id?: number | null;
  after_issue_id?: number | null;
  expected_version?: number;
}

export interface IssuePatchInput extends TaskUpdate {
  expected_version: number;
}

export interface IssueUserSummary {
  id: number;
  username: string;
  full_name: string;
}

export interface IssueComment {
  id: number;
  task_id: number;
  author_id: number;
  content: string;
  parent_id?: number | null;
  created_at: string;
  updated_at: string;
  author: IssueUserSummary;
}

export interface IssueActivity {
  id: number;
  task_id?: number | null;
  project_id?: number | null;
  action: string;
  field?: string | null;
  old_value?: string | null;
  new_value?: string | null;
  created_at: string;
  actor: IssueUserSummary;
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
