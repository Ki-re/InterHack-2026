import asyncio
from pathlib import Path

import google.generativeai as genai
import yaml

from app.core.config import get_settings
from app.llm.schemas import AlertContext, ChatMessage

_PROMPT_PATH = Path(__file__).parent / "prompt.yaml"


def _load_system_prompt(alert: AlertContext) -> str:
    with open(_PROMPT_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    template: str = data["system"]
    return template.format(
        client_name=alert.clientName,
        risk_level=alert.riskLevel,
        churn_probability=alert.churnProbability,
        purchase_propensity=alert.purchasePropensity,
        customer_value=alert.customerValue,
        churn_type=alert.churnType,
        explanation=alert.explanation,
    )


def _build_contents(history: list[ChatMessage], question: str) -> list[dict]:
    """Convert chat history + new question into Gemini contents format."""
    contents = []
    for msg in history:
        role = "user" if msg.role == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg.content}]})
    contents.append({"role": "user", "parts": [{"text": question}]})
    return contents


def _call_gemini(system_prompt: str, contents: list[dict]) -> str:
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=system_prompt,
    )
    response = model.generate_content(contents)
    return response.text


async def get_ai_response(
    alert: AlertContext,
    history: list[ChatMessage],
    question: str,
) -> str:
    system_prompt = _load_system_prompt(alert)
    contents = _build_contents(history, question)
    return await asyncio.to_thread(_call_gemini, system_prompt, contents)
