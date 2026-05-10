from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.regional_dashboard import router as regional_dashboard_router
from app.llm.router import router as llm_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(health_router)
api_router.include_router(llm_router)
api_router.include_router(regional_dashboard_router)
