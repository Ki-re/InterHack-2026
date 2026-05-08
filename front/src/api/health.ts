import { apiRequest } from "@/api/client";

export type HealthResponse = {
  status: string;
};

export function getHealth(): Promise<HealthResponse> {
  return apiRequest<HealthResponse>("/health");
}
