import { apiRequest } from "@/api/client";

export type AuthUser = {
  id: number;
  email: string;
  created_at: string;
};

export type AuthCredentials = {
  email: string;
  password: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: "bearer";
  user: AuthUser;
};

export function register(credentials: AuthCredentials) {
  return apiRequest<AuthResponse>("/auth/register", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(credentials),
  });
}

export function login(credentials: AuthCredentials) {
  return apiRequest<AuthResponse>("/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(credentials),
  });
}

export function getCurrentUser(token: string) {
  return apiRequest<AuthUser>("/auth/me", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}
