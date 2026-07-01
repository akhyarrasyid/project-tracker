import axios from "axios";

export const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

const getStorage = () => globalThis.localStorage;
const reloadWindow = () => {
  globalThis.location.reload();
};

// Let's create a queue for request retries during token refresh
let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

const subscribeTokenRefresh = (cb: (token: string) => void) => {
  refreshSubscribers.push(cb);
};

const onRefreshed = (token: string) => {
  refreshSubscribers.forEach((cb) => {
    cb(token);
  });
  refreshSubscribers = [];
};

// Request Interceptor: Attach access token
client.interceptors.request.use(
  (config) => {
    const token = getStorage().getItem("access_token");
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    throw error;
  }
);

// Response Interceptor: Handle token refresh on 401
client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (!error.response) {
      throw error;
    }

    const status = error.response.status;

    // If 401 and we haven't retried yet
    if (status === 401 && !originalRequest._retry) {
      const isAuthRequest =
        originalRequest.url?.includes("/api/v1/auth/login") ||
        originalRequest.url?.includes("/api/v1/auth/refresh");
      if (isAuthRequest) {
        throw error;
      }

      originalRequest._retry = true;
      const refreshToken = getStorage().getItem("refresh_token");

      if (!refreshToken) {
        throw error;
      }

      if (!isRefreshing) {
        isRefreshing = true;
        try {
          const res = await axios.post(
            `${API_BASE_URL}/api/v1/auth/refresh?refresh_token=${encodeURIComponent(refreshToken)}`
          );
          const { access_token, refresh_token: new_refresh_token } = res.data;
          
          getStorage().setItem("access_token", access_token);
          getStorage().setItem("refresh_token", new_refresh_token);

          isRefreshing = false;
          onRefreshed(access_token);
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return client(originalRequest);
        } catch (refreshError) {
          isRefreshing = false;
          // Clear storage on failed refresh to force login
          getStorage().removeItem("access_token");
          getStorage().removeItem("refresh_token");
          reloadWindow();
          throw refreshError;
        }
      }

      // Queue other requests while token is refreshing
      return new Promise((resolve) => {
        subscribeTokenRefresh((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          resolve(client(originalRequest));
        });
      });
    }

    throw error;
  }
);

export default client;
