import { execSync } from "node:child_process";

import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

function readGitSha() {
  const envSha = process.env.VERCEL_GIT_COMMIT_SHA || process.env.GITHUB_SHA;
  if (envSha) {
    return envSha.slice(0, 12);
  }

  try {
    return execSync("git rev-parse --short=12 HEAD", {
      stdio: ["ignore", "pipe", "ignore"],
    })
      .toString()
      .trim();
  } catch {
    return "unknown";
  }
}

const buildInfo = {
  version: process.env.npm_package_version || "0.0.0",
  gitSha: readGitSha(),
  builtAt: new Date().toISOString(),
};

// https://vite.dev/config/
export default defineConfig({
  define: {
    __APP_BUILD_INFO__: JSON.stringify(buildInfo),
  },
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    fileParallelism: false,
    maxWorkers: 1,
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "lcov", "clover"],
    },
  },
});
