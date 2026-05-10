import { apiRequest } from "@/api/client";
import type { SalesAlert } from "@/types/alerts";

type AlertApiRow = {
  id: string;
  clientName: string;
  riskLevel: "low" | "medium" | "high";
  churnProbability: number;
  purchasePropensity: number;
  customerValue: "low" | "medium" | "high";
  explanation: string;
  churnType: string;
  status: string;
  interactions: SalesAlert["interactions"];
  events: SalesAlert["events"];
  dismissReason?: string | null;
  dismissedAt?: string | null;
  alertContextJson?: string | null;
  predictedNextPurchase?: string | null;
  lastOrderDate?: string | null;
};

export async function fetchAlerts(agentId?: number): Promise<SalesAlert[]> {
  const qs = agentId !== undefined ? `?agent_id=${agentId}` : "";
  const rows = await apiRequest<AlertApiRow[]>(`/alerts${qs}`);
  return rows.map((r) => ({
    id: r.id,
    clientName: r.clientName,
    riskLevel: r.riskLevel,
    churnProbability: r.churnProbability,
    purchasePropensity: r.purchasePropensity,
    customerValue: r.customerValue,
    explanation: r.explanation,
    churnType: r.churnType,
    status: (r.status as SalesAlert["status"]) ?? "pending",
    interactions: r.interactions ?? [],
    events: r.events ?? [],
    dismissReason: r.dismissReason ?? undefined,
    dismissedAt: r.dismissedAt ?? undefined,
    alertContextJson: r.alertContextJson ?? undefined,
    predictedNextPurchase: r.predictedNextPurchase ?? undefined,
    lastOrderDate: r.lastOrderDate ?? undefined,
  }));
}
