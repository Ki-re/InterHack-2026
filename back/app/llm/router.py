from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.llm.schemas import ChatRequest, ChatResponse
from app.llm.service import get_ai_response

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=503,
            detail="GEMINI_API_KEY is not configured on this server.",
        )
    try:
        response_text = await get_ai_response(
            alert=request.alert,
            history=request.history,
            question=request.question,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return ChatResponse(response=response_text)
