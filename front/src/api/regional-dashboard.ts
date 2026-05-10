import { apiRequest } from "@/api/client";
import type { RegionalDashboardResponse } from "@/types/regional-dashboard";

export function getRegionalDashboard(ccaa?: string | null) {
  const url = ccaa ? `/regional-dashboard?ccaa=${ccaa}` : "/regional-dashboard";
  return apiRequest<RegionalDashboardResponse>(url);
}
