export interface UserMe {
  id: number;
  email: string;
  username: string;
  full_name: string;
  role: "admin" | "worker";
  team_id: number;
}
