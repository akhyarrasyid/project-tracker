import { createContext } from "react";

import type { UserMe } from "../types/auth";

export interface AuthContextType {
  user: UserMe | null;
  loading: boolean;
  login: (usernameOrEmail: string, password: string) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);
