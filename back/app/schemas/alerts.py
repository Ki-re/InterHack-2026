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
    status: str             # always "pending" from DB
    interactions: list      # always []
    events: list            # always []
    alertContextJson: str | None = None
    predictedNextPurchase: str | None = None
    lastOrderDate: str | None = None
