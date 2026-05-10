from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


def to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


ExecutionStatus = Literal["attended", "pending", "dismissed"]
RiskLevel = Literal["low", "medium", "high"]
PerformanceStatus = Literal["good", "warning", "critical"]


class ExecutionKpis(CamelModel):
    total_alerts: int
    pending_alerts: int
    attended_alerts: int
    dismissed_alerts: int
    attended_rate: int
    dismissal_rate: int
    high_risk_backlog: int
    overdue_followups: int
    average_response_hours: float | None
    execution_score: int
    status: PerformanceStatus


class AlertExecution(CamelModel):
    id: int
    status: ExecutionStatus
    risk_level: RiskLevel
    churn_probability: int
    purchase_propensity: int
    estimated_value: float
    created_at: datetime
    due_at: datetime
    attended_at: datetime | None
    dismissed_at: datetime | None


class ClientExecution(CamelModel):
    id: int
    name: str
    customer_value: str
    segment: str
    kpis: ExecutionKpis
    alerts: list[AlertExecution]


class AgentPerformance(CamelModel):
    id: int
    name: str
    email: str
    cod_ccaa: str
    kpis: ExecutionKpis
    clients: list[ClientExecution]


class ManagerPerformance(CamelModel):
    id: int
    name: str
    email: str
    kpis: ExecutionKpis
    agents: list[AgentPerformance]


class CcaaKpis(CamelModel):
    cod_ccaa: str
    kpis: ExecutionKpis


class RegionSummary(CamelModel):
    id: int
    slug: str
    name: str
    kpis: ExecutionKpis
    managers: list[ManagerPerformance]
    ccaa_kpis: list[CcaaKpis]


class Underperformer(CamelModel):
    level: Literal["manager", "agent"]
    id: int
    name: str
    parent_name: str | None
    region_slug: str
    execution_score: int
    pending_alerts: int
    high_risk_backlog: int
    overdue_followups: int


class RegionalDashboardResponse(CamelModel):
    generated_at: datetime
    kpis: ExecutionKpis
    regions: list[RegionSummary]
    underperformers: list[Underperformer]
