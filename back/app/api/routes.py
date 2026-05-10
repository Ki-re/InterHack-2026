from fastapi import APIRouter

from app.api.agents import router as agents_router
from app.api.alerts import router as alerts_router
from app.api.audio import router as audio_router
from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.notifications import router as notifications_router
from app.api.regional_dashboard import router as regional_dashboard_router
from app.llm.router import router as llm_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(health_router)
api_router.include_router(llm_router)
api_router.include_router(audio_router)
api_router.include_router(regional_dashboard_router)
api_router.include_router(notifications_router)
api_router.include_router(alerts_router)
api_router.include_router(agents_router)
