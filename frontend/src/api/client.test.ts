import { beforeEach, describe, expect, it, vi } from "vitest";

let requestFulfilled: ((config: { headers?: Record<string, string> }) => { headers?: Record<string, string> }) | undefined;
let responseRejected:
  | ((
      error: {
        config: Record<string, any>;
        response?: { status: number };
      },
    ) => Promise<unknown>)
  | undefined;

const clientInstance = Object.assign(
  vi.fn(async (config: Record<string, any>) => ({ data: { retried: true, config } })),
  {
    interceptors: {
      request: {
        use: vi.fn((fulfilled: typeof requestFulfilled) => {
          requestFulfilled = fulfilled;
        }),
      },
      response: {
        use: vi.fn((_fulfilled: unknown, rejected: typeof responseRejected) => {
          responseRejected = rejected;
        }),
      },
    },
  },
);

const axiosPost = vi.fn();

vi.mock("axios", () => ({
  default: {
    create: vi.fn(() => clientInstance),
    post: axiosPost,
  },
}));

describe("client", () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    vi.resetModules();
    localStorage.clear();
    requestFulfilled = undefined;
    responseRejected = undefined;
    Object.defineProperty(window, "location", {
      value: { reload: vi.fn() },
      configurable: true,
    });
    await import("./client");
  });

  it("attaches the bearer token on request", () => {
    localStorage.setItem("access_token", "demo-token");

    const result = requestFulfilled?.({ headers: {} });

    expect(result?.headers?.Authorization).toBe("Bearer demo-token");
  });

  it("rejects login refresh loops immediately", async () => {
    await expect(
      responseRejected?.({
        config: { _retry: false, url: "/api/v1/auth/login", headers: {} },
        response: { status: 401 },
      }) ?? Promise.resolve(),
    ).rejects.toEqual(
      expect.objectContaining({
        response: { status: 401 },
      }),
    );
  });

  it("rejects 401 requests when there is no refresh token", async () => {
    await expect(
      responseRejected?.({
        config: { _retry: false, url: "/api/v1/projects/1", headers: {} },
        response: { status: 401 },
      }) ?? Promise.resolve(),
    ).rejects.toEqual(
      expect.objectContaining({
        response: { status: 401 },
      }),
    );
  });

  it("refreshes the token and retries the original request", async () => {
    localStorage.setItem("refresh_token", "refresh-token");
    axiosPost.mockResolvedValue({
      data: {
        access_token: "new-access",
        refresh_token: "new-refresh",
      },
    });

    const result = await responseRejected?.({
      config: { _retry: false, url: "/api/v1/projects/1", headers: {} },
      response: { status: 401 },
    });

    expect(axiosPost).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/auth/refresh?refresh_token=refresh-token"),
    );
    expect(localStorage.getItem("access_token")).toBe("new-access");
    expect(localStorage.getItem("refresh_token")).toBe("new-refresh");
    expect(clientInstance).toHaveBeenCalledWith(
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer new-access",
        }),
      }),
    );
    expect(result).toEqual(
      expect.objectContaining({
        data: expect.objectContaining({ retried: true }),
      }),
    );
  });

  it("clears auth state and reloads when refresh fails", async () => {
    localStorage.setItem("access_token", "old-access");
    localStorage.setItem("refresh_token", "old-refresh");
    axiosPost.mockRejectedValue(new Error("refresh failed"));

    await expect(
      responseRejected?.({
        config: { _retry: false, url: "/api/v1/projects/1", headers: {} },
        response: { status: 401 },
      }) ?? Promise.resolve(),
    ).rejects.toThrow("refresh failed");

    expect(localStorage.getItem("access_token")).toBeNull();
    expect(localStorage.getItem("refresh_token")).toBeNull();
    expect(window.location.reload).toHaveBeenCalledTimes(1);
  });
});
