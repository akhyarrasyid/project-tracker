import client from "./client";
import type { Department, Team, ProjectMeta, UserMeta } from "../types/meta";

export const metaApi = {
  getDepartments: async (): Promise<Department[]> => {
    const response = await client.get<Department[]>("/api/v1/meta/departments");
    return response.data;
  },

  getTeams: async (departmentId?: number): Promise<Team[]> => {
    const params = departmentId !== undefined ? { department_id: departmentId } : {};
    const response = await client.get<Team[]>("/api/v1/meta/teams", { params });
    return response.data;
  },

  getProjects: async (teamId?: number): Promise<ProjectMeta[]> => {
    const params = teamId !== undefined ? { team_id: teamId } : {};
    const response = await client.get<ProjectMeta[]>("/api/v1/meta/projects", { params });
    return response.data;
  },

  getUsers: async (projectId?: number): Promise<UserMeta[]> => {
    const params = projectId !== undefined ? { project_id: projectId } : {};
    const response = await client.get<UserMeta[]>("/api/v1/meta/users", { params });
    return response.data;
  },
};
