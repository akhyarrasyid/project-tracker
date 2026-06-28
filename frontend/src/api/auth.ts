import client from "./client";
import type { UserMe } from "../types/auth";

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export const authApi = {
  login: async (usernameOrEmail: string, password: string): Promise<TokenResponse> => {
    // Standard OAuth2 Form Data request
    const params = new URLSearchParams();
    params.append("username", usernameOrEmail);
    params.append("password", password);

    const response = await client.post<TokenResponse>("/api/v1/auth/login", params, {
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });
    return response.data;
  },

  getMe: async (): Promise<UserMe> => {
    const response = await client.get<UserMe>("/api/v1/auth/me");
    return response.data;
  },
};
