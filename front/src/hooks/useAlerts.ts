import { useQuery } from "@tanstack/react-query";

import { fetchAlerts } from "@/api/alerts";

export function useAlerts() {
  return useQuery({
    queryKey: ["alerts"],
    queryFn: fetchAlerts,
    staleTime: 60_000,
  });
}
