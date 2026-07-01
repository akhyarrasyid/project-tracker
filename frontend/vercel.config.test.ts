import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

describe("frontend vercel spa routing", () => {
  it("rewrites client-side routes to index.html", () => {
    const raw = readFileSync(resolve(__dirname, "vercel.json"), "utf-8");
    const config = JSON.parse(raw) as {
      rewrites?: Array<{ source: string; destination: string }>;
    };

    expect(config.rewrites).toEqual([
      {
        source: "/(.*)",
        destination: "/index.html",
      },
    ]);
  });
});
