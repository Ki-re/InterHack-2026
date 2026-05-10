"""Static mock alert data mirroring the frontend mock-alerts.ts.
Used by the notification scheduler to find high-priority unresolved alerts.
In a real system this would query the alerts DB table.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

_MOCK_ALERTS = [
    {"id": "alert-001", "clientName": "Clínica Dental Armonía", "riskLevel": "high", "status": "pending", "days_old": 5},
    {"id": "alert-002", "clientName": "Dentalia Grup Llevant", "riskLevel": "medium", "status": "pending", "days_old": 3},
    {"id": "alert-003", "clientName": "Centre Odontològic Baix Llobregat", "riskLevel": "low", "status": "pending", "days_old": 1},
    {"id": "alert-004", "clientName": "Estudi Dental Sants", "riskLevel": "high", "status": "pending", "days_old": 7},
    {"id": "alert-005", "clientName": "Clínica Dental Provença", "riskLevel": "high", "status": "pending", "days_old": 4},
    {"id": "alert-006", "clientName": "Oral·lent Granollers", "riskLevel": "medium", "status": "pending", "days_old": 2},
    {"id": "alert-007", "clientName": "Centre Dental Badalona", "riskLevel": "high", "status": "attended", "days_old": 6},
    {"id": "alert-008", "clientName": "Clínica Dental Sabadell Nord", "riskLevel": "high", "status": "pending", "days_old": 3},
]


def get_pending_high_risk_alerts(min_days_old: int = 2) -> list[dict]:
    """Return high-risk pending alerts older than min_days_old days."""
    return [
        a for a in _MOCK_ALERTS
        if a["riskLevel"] == "high"
        and a["status"] == "pending"
        and a["days_old"] >= min_days_old
    ]
