import { useQuery } from "@tanstack/react-query";

import { fetchAlerts } from "@/api/alerts";

export function useAlerts(agentId?: number) {
  return useQuery({
    queryKey: ["alerts", agentId],
    queryFn: () => fetchAlerts(agentId),
    staleTime: 60_000,
    enabled: agentId !== undefined,
  });
}
