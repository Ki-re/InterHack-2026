export type RiskLevel = "low" | "medium" | "high";

export type CustomerValue = "low" | "medium" | "high";

export type ChurnType = "total" | string;

export type AlertStatus = "pending" | "attended";

export type HandlingChannel = "phone" | "visit" | "email" | "other";

export type InteractionResult = "positive" | "neutral" | "negative";

export type FollowUpRecord = {
  handledBy: HandlingChannel;
  result: InteractionResult;
  reminder: string;
  submittedAt: string;
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
  followUp?: FollowUpRecord;
};
