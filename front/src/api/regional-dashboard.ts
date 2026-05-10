import { apiRequest } from "@/api/client";
import type { RegionalDashboardResponse } from "@/types/regional-dashboard";

export function getRegionalDashboard() {
  return apiRequest<RegionalDashboardResponse>("/regional-dashboard");
}
