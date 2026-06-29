import React, { useEffect, useState } from "react";

import { authApi } from "../api/auth";
import type { UserMe } from "../types/auth";
import { AuthContext } from "./auth-context";

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [user, setUser] = useState<UserMe | null>(null);
  const [loading, setLoading] = useState(true);

  const loadUser = async () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setLoading(false);
      return;
    }

    try {
      const data = await authApi.getMe();
      setUser(data);
    } catch {
      // Access token invalid or expired. The axios interceptor handles refresh automatically,
      // but if the refresh also fails, we clear state.
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUser();
  }, []);

  const login = async (usernameOrEmail: string, password: string) => {
    setLoading(true);
    try {
      const res = await authApi.login(usernameOrEmail, password);
      localStorage.setItem("access_token", res.access_token);
      localStorage.setItem("refresh_token", res.refresh_token);
      const profile = await authApi.getMe();
      setUser(profile);
    } catch (error) {
      setUser(null);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
