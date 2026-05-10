from typing import Literal

from pydantic import BaseModel


class AlertContext(BaseModel):
    clientName: str
    riskLevel: str
    churnProbability: int
    purchasePropensity: int
    customerValue: str
    churnType: str
    explanation: str
    alertContextJson: str | None = None
    predictedNextPurchase: str | None = None
    lastOrderDate: str | None = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    alert: AlertContext
    history: list[ChatMessage] = []
    question: str


class ChatResponse(BaseModel):
    response: str
