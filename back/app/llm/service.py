import asyncio
from pathlib import Path

import yaml
from google import genai
from google.genai import types

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


def _build_contents(history: list[ChatMessage], question: str) -> list[types.Content]:
    """Convert chat history + new question into Gemini contents format."""
    contents = []
    for msg in history:
        role = "user" if msg.role == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=msg.content)]))
    contents.append(types.Content(role="user", parts=[types.Part(text=question)]))
    return contents


def _call_gemini(system_prompt: str, contents: list[types.Content]) -> str:
    settings = get_settings()
    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=contents,
        config=types.GenerateContentConfig(system_instruction=system_prompt),
    )
    return response.text


async def get_ai_response(
    alert: AlertContext,
    history: list[ChatMessage],
    question: str,
) -> str:
    system_prompt = _load_system_prompt(alert)
    contents = _build_contents(history, question)
    return await asyncio.to_thread(_call_gemini, system_prompt, contents)
