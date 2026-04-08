import client from "./client";

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface User {
  id: number;
  email: string;
  name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export const authApi = {
  login: (data: LoginRequest) =>
    client.post<TokenResponse>("/auth/login", data),

  getMe: () => client.get<User>("/auth/me"),
};
