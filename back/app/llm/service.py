import asyncio
import json
from pathlib import Path

import yaml
from google import genai
from google.genai import types

from app.core.config import get_settings
from app.llm.schemas import AlertContext, ChatMessage

_PROMPT_PATH = Path(__file__).parent / "prompt.yaml"


_CTX_LABELS: dict[str, dict[str, str]] = {
    "es": {
        "predicted_next_purchase": "Próxima compra estimada",
        "last_order_date": "Fecha último pedido",
        "annual_spend_real": "Gasto anual (real)",
        "annual_spend_expected": "Gasto anual (esperado)",
        "days_since_purchase": "Días desde última compra",
        "avg_days_between": "Días medios entre compras (producto)",
        "momentum_zscore": "Z-score de ritmo de compra",
        "potential_class": "Clase de potencial",
        "prior_purchases": "Compras previas (producto)",
        "repurchase_yes": "Modelo predice recompra: sí",
        "repurchase_no": "Modelo predice recompra: no",
        "additional_context": "Contexto adicional",
    },
    "ca": {
        "predicted_next_purchase": "Pròxima compra estimada",
        "last_order_date": "Data darrera comanda",
        "annual_spend_real": "Despesa anual (real)",
        "annual_spend_expected": "Despesa anual (esperada)",
        "days_since_purchase": "Dies des de la darrera compra",
        "avg_days_between": "Dies mitjans entre compres (producte)",
        "momentum_zscore": "Z-score de ritme de compra",
        "potential_class": "Classe de potencial",
        "prior_purchases": "Compres prèvies (producte)",
        "repurchase_yes": "El model prediu recompra: sí",
        "repurchase_no": "El model prediu recompra: no",
        "additional_context": "Context addicional",
    },
}


def _build_context_block(alert: AlertContext, lang: str = "es") -> str:
    lbl = _CTX_LABELS.get(lang, _CTX_LABELS["es"])
    lines = []
    if alert.predictedNextPurchase:
        lines.append(f"{lbl['predicted_next_purchase']}: {alert.predictedNextPurchase}")
    if alert.lastOrderDate:
        lines.append(f"{lbl['last_order_date']}: {alert.lastOrderDate}")
    if alert.alertContextJson:
        try:
            ctx = json.loads(alert.alertContextJson)
            if ctx.get("ctx_gasto_anual_real"):
                lines.append(f"{lbl['annual_spend_real']}: {ctx['ctx_gasto_anual_real']}€")
            if ctx.get("ctx_gasto_esperado"):
                lines.append(f"{lbl['annual_spend_expected']}: {ctx['ctx_gasto_esperado']}€")
            if ctx.get("ctx_dias_desde_compra"):
                lines.append(f"{lbl['days_since_purchase']}: {ctx['ctx_dias_desde_compra']}")
            if ctx.get("ctx_tiempo_medio_recompra"):
                try:
                    avg_days = round(float(ctx["ctx_tiempo_medio_recompra"]))
                    lines.append(f"{lbl['avg_days_between']}: {avg_days}")
                except (ValueError, TypeError):
                    pass
            if ctx.get("ctx_zscore_momento"):
                lines.append(f"{lbl['momentum_zscore']}: {ctx['ctx_zscore_momento']}")
            if ctx.get("ctx_potencial_clase"):
                lines.append(f"{lbl['potential_class']}: {ctx['ctx_potencial_clase']}")
            if ctx.get("ctx_num_compras_anteriores"):
                lines.append(f"{lbl['prior_purchases']}: {ctx['ctx_num_compras_anteriores']}")
            vuelve = ctx.get("ctx_vuelve_a_comprar", "")
            if vuelve != "":
                key = "repurchase_yes" if str(vuelve) == "1" else "repurchase_no"
                lines.append(lbl[key])
        except (json.JSONDecodeError, TypeError):
            pass
    if not lines:
        return ""
    return f"{lbl['additional_context']}:\n" + "\n".join(f"  {l}" for l in lines)


_LANG_NAMES = {"ca": "Catalan", "es": "Spanish"}


def _load_system_prompt(alert: AlertContext, lang: str = "es") -> str:
    with open(_PROMPT_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    template: str = data["system"]
    lang_name = _LANG_NAMES.get(lang, "Spanish")
    return template.format(
        client_name=alert.clientName,
        risk_level=alert.riskLevel,
        churn_probability=alert.churnProbability,
        purchase_propensity=alert.purchasePropensity,
        customer_value=alert.customerValue,
        churn_type=alert.churnType,
        explanation=alert.explanation,
        context_block=_build_context_block(alert, lang),
        ui_language=lang_name,
    )


def _build_contents(history: list[ChatMessage], question: str) -> list[types.Content]:
    """Convert chat history + new question into Gemini contents format."""
    contents = []
    for msg in history:
        role = "user" if msg.role == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg.content)]))
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=question)]))
    return contents


def _call_gemini(system_prompt: str, contents: list[types.Content]) -> str:
    settings = get_settings()
    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=types.GenerateContentConfig(system_instruction=system_prompt),
    )
    return response.text


async def get_ai_response(
    alert: AlertContext,
    history: list[ChatMessage],
    question: str,
    lang: str = "es",
) -> str:
    system_prompt = _load_system_prompt(alert, lang)
    contents = _build_contents(history, question)
    return await asyncio.to_thread(_call_gemini, system_prompt, contents)
