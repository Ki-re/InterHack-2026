from pydantic import BaseModel


class SalesAlertResponse(BaseModel):
    id: str
    clientName: str
    riskLevel: str          # "low" | "medium" | "high"
    churnProbability: int
    purchasePropensity: int
    customerValue: str      # "low" | "medium" | "high"
    explanation: str
    churnType: str
    status: str             # "pending" | "attended" | "dismissed"
    interactions: list      # InteractionRecord[] — populated from DB
    events: list            # SystemEventRecord[] — populated from DB
    dismissReason: str | None = None
    dismissedAt: str | None = None
    alertContextJson: str | None = None
    predictedNextPurchase: str | None = None
    lastOrderDate: str | None = None
