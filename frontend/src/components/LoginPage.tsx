import React, { useState } from "react";
import { MoonStar, SunMedium } from "lucide-react";

import projectTrackerLogo from "../assets/logo project tracker.png";
import { getBuildLabel } from "../app/build-info";
import { useTheme } from "../app/theme";
import { useAuth } from "../contexts/useAuth";

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const buildLabel = getBuildLabel();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError("Username/email dan password wajib diisi");
      return;
    }
    setError("");
    setLoading(true);
    try {
      await login(username, password);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Gagal masuk. Periksa kembali akun Anda.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-shell relative flex min-h-screen items-center justify-center overflow-hidden font-sans">
      <div className="absolute left-[-10%] top-[-20%] h-[60%] w-[60%] rounded-full bg-blue-600/12 blur-[120px]" />
      <div className="absolute bottom-[-20%] right-[-10%] h-[60%] w-[60%] rounded-full bg-violet-600/10 blur-[120px]" />

      <button
        type="button"
        onClick={toggleTheme}
        className="absolute right-6 top-6 z-20 rounded-xl border border-white/10 bg-[color:var(--app-panel)] px-3 py-2 text-sm text-[color:var(--app-text-soft)] shadow-sm backdrop-blur hover:text-[color:var(--app-heading)]"
        aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      >
        <span className="inline-flex items-center gap-2">
          {theme === "dark" ? <SunMedium className="h-4 w-4" /> : <MoonStar className="h-4 w-4" />}
          {theme === "dark" ? "Light" : "Dark"}
        </span>
      </button>

      <div className="z-10 w-full max-w-md px-6">
        <div className="app-panel flex flex-col gap-6 rounded-[28px] p-8 backdrop-blur-xl">
          <div className="flex flex-col items-center gap-2.5 text-center">
            <img
              src={projectTrackerLogo}
              alt="Project Tracker"
              className="h-16 w-16 rounded-2xl bg-white/95 object-cover p-1 shadow-[0_16px_34px_rgba(37,99,235,0.22)]"
            />
            <div>
              <h2 className="text-xl font-extrabold tracking-tight text-[color:var(--app-heading)]">
                Project Tracker
              </h2>
              <p className="text-xs font-medium text-[color:var(--app-text-soft)]">
                Enterprise Workspace Portal
              </p>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            {error && (
              <div className="flex items-center gap-2 rounded-2xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-xs font-semibold text-red-500">
                <svg className="h-4 w-4 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                    clipRule="evenodd"
                  />
                </svg>
                <span>{error}</span>
              </div>
            )}

            <div className="flex flex-col gap-1.5">
              <label
                htmlFor="username-input"
                className="text-xs font-semibold tracking-[0.18em] text-[color:var(--app-text-soft)]"
              >
                Username / Email
              </label>
              <input
                id="username-input"
                type="text"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="admin atau email Anda"
                className="w-full rounded-2xl border border-[color:var(--app-border)] bg-[color:var(--app-panel-strong)] px-4 py-3 text-sm text-[color:var(--app-heading)] outline-none placeholder:text-[color:var(--app-text-faint)] focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label
                htmlFor="password-input"
                className="text-xs font-semibold tracking-[0.18em] text-[color:var(--app-text-soft)]"
              >
                Password
              </label>
              <input
                id="password-input"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full rounded-2xl border border-[color:var(--app-border)] bg-[color:var(--app-panel-strong)] px-4 py-3 text-sm text-[color:var(--app-heading)] outline-none placeholder:text-[color:var(--app-text-faint)] focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="mt-2 h-11 w-full rounded-2xl bg-blue-600 text-sm font-semibold text-white shadow-[0_14px_30px_rgba(37,99,235,0.24)] transition-all hover:bg-blue-500 active:scale-[0.98] disabled:opacity-50"
            >
              {loading ? "Masuk..." : "Masuk ke Workspace"}
            </button>
          </form>
          <div className="text-center text-[11px] text-[color:var(--app-text-faint)]" data-testid="build-identity">
            Build {buildLabel}
          </div>
        </div>
      </div>
    </div>
  );
};
