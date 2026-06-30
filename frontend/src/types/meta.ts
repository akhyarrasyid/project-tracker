export interface Department {
  id: number;
  name: string;
  description?: string;
}

export interface Team {
  id: number;
  name: string;
  department_id: number;
  description?: string;
}

export interface ProjectMeta {
  id: number;
  name: string;
  key: string;
  description?: string | null;
  status: string;
}

export interface ProjectSummary {
  total_issues: number;
  done_issues: number;
  active_issues: number;
  issue_progress_percent: number;
  point_progress_percent: number;
  blocked_count: number;
  overdue_count: number;
  at_risk_count: number;
}

export interface UserMeta {
  id: number;
  full_name: string;
  email: string;
}
