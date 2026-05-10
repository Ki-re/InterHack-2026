export type RegionSlug = "east" | "north" | "south" | "canary" | "balearic";

export type ExecutionStatus = "attended" | "pending" | "dismissed";

export type RiskLevel = "low" | "medium" | "high";

export type PerformanceStatus = "good" | "warning" | "critical";

export type ExecutionKpis = {
  totalAlerts: number;
  pendingAlerts: number;
  attendedAlerts: number;
  dismissedAlerts: number;
  attendedRate: number;
  dismissalRate: number;
  highRiskBacklog: number;
  overdueFollowups: number;
  averageResponseHours: number | null;
  executionScore: number;
  status: PerformanceStatus;
};

export type AlertExecution = {
  id: number;
  status: ExecutionStatus;
  riskLevel: RiskLevel;
  churnProbability: number;
  purchasePropensity: number;
  estimatedValue: number;
  createdAt: string;
  dueAt: string;
  attendedAt: string | null;
  dismissedAt: string | null;
};

export type ClientExecution = {
  id: number;
  name: string;
  customerValue: string;
  segment: string;
  kpis: ExecutionKpis;
  alerts: AlertExecution[];
};

export type AgentPerformance = {
  id: number;
  name: string;
  email: string;
  codCcaa: string;
  kpis: ExecutionKpis;
  clients: ClientExecution[];
};

export type ManagerPerformance = {
  id: number;
  name: string;
  email: string;
  kpis: ExecutionKpis;
  agents: AgentPerformance[];
};

export type CcaaKpis = {
  codCcaa: string;
  kpis: ExecutionKpis;
};

export type RegionSummary = {
  id: number;
  slug: RegionSlug;
  name: string;
  kpis: ExecutionKpis;
  managers: ManagerPerformance[];
  ccaaKpis: CcaaKpis[];
};

export type Underperformer = {
  level: "manager" | "agent";
  id: number;
  name: string;
  parentName: string | null;
  regionSlug: RegionSlug;
  executionScore: number;
  pendingAlerts: number;
  highRiskBacklog: number;
  overdueFollowups: number;
};

export type RegionalDashboardResponse = {
  generatedAt: string;
  kpis: ExecutionKpis;
  regions: RegionSummary[];
  underperformers: Underperformer[];
};
