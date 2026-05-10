export type RiskLevel = "low" | "medium" | "high";

export type CustomerValue = "low" | "medium" | "high";

export type ChurnType = "total" | string;

export type AlertStatus = "pending" | "attended" | "dismissed";

export type HandlingChannel = "phone" | "visit" | "email" | "other";

export type InteractionResult = "positive" | "neutral" | "negative";

export type InteractionRecord = {
  id: string;
  handledBy: HandlingChannel;
  answered?: boolean;               // phone only
  visitSuccessful?: boolean;        // visit only
  emailResponseReceived?: boolean;  // email only
  result?: InteractionResult;       // only when contact was successful
  notes?: string;
  keepOpen: boolean;
  submittedAt: string;
};

export type SystemEventType = "closed" | "dismissed" | "reopened";

export type SystemEventRecord = {
  id: string;
  type: SystemEventType;
  reason?: string;
  timestamp: string;
};

export type SalesAlert = {
  id: string;
  clientName: string;
  riskLevel: RiskLevel;
  churnProbability: number;
  purchasePropensity: number;
  customerValue: CustomerValue;
  explanation: string;
  churnType: ChurnType;
  status: AlertStatus;
  interactions: InteractionRecord[];
  events: SystemEventRecord[];
  dismissReason?: string;
  dismissedAt?: string;
  alertContextJson?: string;
  predictedNextPurchase?: string;
  lastOrderDate?: string;
};
