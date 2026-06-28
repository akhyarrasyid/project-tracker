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
  status: string;
}

export interface UserMeta {
  id: number;
  full_name: string;
  email: string;
}
