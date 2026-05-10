"""
generate_alerts.py
==================
Alerting pipeline for INIBSA commercial dashboard.

Reads `predicciones.csv` (ML inference output) and produces `alerts.csv`
containing only the alerts that the dashboard should display.

The pipeline:
  1. Determines a temporal inference window from the dataset's latest buy date:
       window = [latest_date − LOOKBACK_MONTHS,  latest_date − RECENCY_EXCLUSION_MONTHS]
     Orders outside this window are excluded (too fresh or too stale).
  2. Takes the LATEST prediction row per (client, product) within the window.
  3. Classifies each client's value tier (Alto / Medio / Bajo) by total spend.
  3b. Computes percentile rank of score_riesgo_0_100 within the candidate set,
      so risk scores are uniformly distributed (0-100) instead of border-heavy.
  4. Computes a combined alert score per (client, product).
  5. Decides alert type per client:
       "Total"    → ≥ MULTI_PRODUCT_THRESHOLD products trigger
       "Combinat" → COMBINED_ALERT_MIN_PRODUCTS ≤ n < MULTI_PRODUCT_THRESHOLD
       "Producto X" → only 1 product triggers
  6. Assigns alert risk level (Alto / Medio / Bajo).
  7. Maps provincia → Comunidad Autónoma → commercial zone → agent ID.
  8. Generates a human-readable explanation for the LLM context.
  9. Writes alerts.csv.

Run:
    python generate_alerts.py

Output:
    alerts.csv  (same directory as this script)
"""

import math
import random
import hashlib
import datetime
import os

import pandas as pd

# ---------------------------------------------------------------------------
# Import deanonymize module (must be in the same directory)
# ---------------------------------------------------------------------------
from deanonymize import get_client_name

# =============================================================================
# TUNEABLE PARAMETERS — adjust these to control alert volume and thresholds
# =============================================================================

# --- Raw churn risk thresholds per client value tier -----------------------
# These are MINIMUM score_riesgo_0_100 values for a (client, product) pair
# to be considered as an alert candidate within each tier.
# Lowering a threshold surfaces more alerts for that tier.

RISK_THRESHOLD_ALTO  = 75.0  # Top-spend clients (top 25%) — alert from risk≥75
RISK_THRESHOLD_MEDIO = 82.0  # Mid-spend clients — alert from risk≥82
RISK_THRESHOLD_BAJO  = 90.0  # Low-spend clients — alert from risk≥90

# --- Purchase propensity filter (optional tightening) ----------------------
# Minimum score_potencial_0_100 to emit an alert.
# Set to 0.0 to disable this filter entirely.
# High propensity + high risk = client buying elsewhere (most actionable).
MIN_PROPENSITY_THRESHOLD = 0.0

# Alert risk-level thresholds (applied to composite score, 0–100 scale)
# Composite = risk*0.50 + propensity*0.30 + value_score*0.20
# where value_score: Alto=100, Medio=60, Bajo=25
# Calibrated to the dataset's composite distribution (P25≈68, P75≈88):
HIGH_ALERT_RISK_THRESHOLD   = 85.0  # composite ≥ 85 → "Alto"   (~top 30%)
MEDIUM_ALERT_RISK_THRESHOLD = 68.0  # composite ≥ 68 → "Medio"  (~next 45%)
# Below MEDIUM_ALERT_RISK_THRESHOLD → "Bajo"               (~bottom 25%)

# --- Client value classification -------------------------------------------

# Percentile boundaries for total historical spend (Valores_H summed per client)
CLIENT_VALUE_HIGH_PERCENTILE = 0.75  # top 25 % → "Alto"
CLIENT_VALUE_LOW_PERCENTILE  = 0.25  # bottom 25 % → "Bajo"
# Middle band → "Medio"

# Scoring multipliers (used for PRIORITY sorting only, not for filtering)
VALUE_MULTIPLIERS = {
    "Alto":  1.0,
    "Medio": 0.7,
    "Bajo":  0.4,
}

# --- Alert type (Total vs Combined vs per-product) -------------------------

# If a client has at least this many products crossing its tier risk threshold,
# collapse them into a single "Total" alert.
MULTI_PRODUCT_THRESHOLD = 3

# If a client has at least this many triggering products (but fewer than
# MULTI_PRODUCT_THRESHOLD), collapse them into a single "Combined" alert
# instead of emitting one alert per product. This reduces alert flooding.
# Must be ≥ 2 and < MULTI_PRODUCT_THRESHOLD.
COMBINED_ALERT_MIN_PRODUCTS = 2  # 2 products → one "Combinat" alert

# For clients with only 1 triggering product, emit a single per-product alert.
MAX_PRODUCT_ALERTS_PER_CLIENT = 1  # kept for safety; effectively always 1 now

# --- Per-tier alert caps (prevents flooding from any single tier) -----------
MAX_ALERTS_ALTO  = 250
MAX_ALERTS_MEDIO = 250
MAX_ALERTS_BAJO  = 100

# --- Temporal inference window ----------------------------------------------
# The pipeline uses the latest buy date in the entire dataset as the
# "reference date" (i.e., the simulated "now" of the inference run).
#
# RECENCY_EXCLUSION_MONTHS: orders made within this many months before the
#   reference date are excluded. Clients who ordered very recently are not
#   yet at risk — alerting them would create noise.
#   Example: 3 → exclude orders from the last 3 months.
#
# LOOKBACK_MONTHS: maximum age (in months before the reference date) of the
#   latest qualifying order. Orders older than this are considered too stale
#   to generate actionable alerts — the relationship may already be lost.
#   Example: 18 → 1.5 years back from the reference date.
#
# The effective window for "current" orders is:
#   [reference_date − LOOKBACK_MONTHS, reference_date − RECENCY_EXCLUSION_MONTHS]
#
# For each (client, product), the LATEST row within this window is used.
# Pairs where no order falls in the window are silently skipped.

RECENCY_EXCLUSION_MONTHS = 3   # Exclude the most recent N months (orders too fresh)
LOOKBACK_MONTHS          = 18  # Maximum staleness in months (1.5 years)

# =============================================================================
# DISPLAY SCORE RESCALING PARAMETERS
# =============================================================================
# After the final alert set is capped and sorted, both churn_probability and
# purchase_propensity are min-max rescaled to a human-readable range.
# This prevents all alerts from clustering at extreme values (e.g. 96–100%)
# and creates meaningful visual spread across the dashboard.
#
# DISPLAY_SCORE_MIN: the lowest displayed % for the least-risky alert in the set
# DISPLAY_SCORE_MAX: the highest displayed % for the most-risky alert in the set
# Increasing the range gives more visual spread; adjust to taste.

DISPLAY_SCORE_MIN = 38.0  # lowest churn% shown on dashboard (for least-risky alert)
DISPLAY_SCORE_MAX = 94.0  # highest churn% shown on dashboard (for most-risky alert)

DISPLAY_PROPENSITY_MIN = 30.0  # lowest propensity% shown on dashboard
DISPLAY_PROPENSITY_MAX = 92.0  # highest propensity% shown on dashboard

# =============================================================================
# RISK LEVEL DISTRIBUTION PARAMETERS
# =============================================================================
# After capping, risk levels are assigned by within-set percentile of alert_score
# (rather than absolute composite thresholds) so every agent always sees a
# realistic mix of Alto / Medio / Bajo alerts.
#
# RISK_LEVEL_HIGH_PCT:   top fraction of alerts that receive "Alto" (high) label
# RISK_LEVEL_MEDIUM_PCT: next fraction that receives "Medio" (medium) label
# The remaining fraction receives "Bajo" (low) label.
# Must sum to ≤ 1.0. The fractions below give ~1/3 of each level.

RISK_LEVEL_HIGH_PCT   = 0.33  # top 33 % → "Alto"
RISK_LEVEL_MEDIUM_PCT = 0.42  # next 42 % → "Medio"
# remainder (≈ 25 %) → "Bajo"

# =============================================================================
# PROVINCE → COMUNIDAD AUTÓNOMA MAPPING
# =============================================================================

PROVINCIA_TO_CCAA: dict[str, str] = {
    # Andalucía
    "Almería":    "Andalucía",
    "Cádiz":      "Andalucía",
    "Córdoba":    "Andalucía",
    "Granada":    "Andalucía",
    "Huelva":     "Andalucía",
    "Jaén":       "Andalucía",
    "Málaga":     "Andalucía",
    "Sevilla":    "Andalucía",
    # Aragón
    "Huesca":     "Aragón",
    "Teruel":     "Aragón",
    "Zaragoza":   "Aragón",
    # Asturias
    "Asturias":   "Asturias",
    # Illes Balears
    "Baleares":   "Illes Balears",
    # Canarias
    "Las Palmas":       "Canarias",
    "Sta.Cruz Tenerife": "Canarias",
    # Cantabria
    "Cantabria":  "Cantabria",
    # Castilla y León
    "Ávila":      "Castilla y León",
    "Burgos":     "Castilla y León",
    "León":       "Castilla y León",
    "Palencia":   "Castilla y León",
    "Salamanca":  "Castilla y León",
    "Segovia":    "Castilla y León",
    "Soria":      "Castilla y León",
    "Valladolid": "Castilla y León",
    "Zamora":     "Castilla y León",
    # Castilla-La Mancha
    "Albacete":     "Castilla-La Mancha",
    "Ciudad Real":  "Castilla-La Mancha",
    "Cuenca":       "Castilla-La Mancha",
    "Guadalajara":  "Castilla-La Mancha",
    "Toledo":       "Castilla-La Mancha",
    # Cataluña
    "Barcelona":  "Cataluña",
    "Girona":     "Cataluña",
    "Lleida":     "Cataluña",
    "Tarragona":  "Cataluña",
    # Comunitat Valenciana
    "Alicante":   "Comunitat Valenciana",
    "Castellón":  "Comunitat Valenciana",
    "Valencia":   "Comunitat Valenciana",
    # Extremadura
    "Badajoz":    "Extremadura",
    "Cáceres":    "Extremadura",
    # Galicia
    "A Coruña":   "Galicia",
    "Lugo":       "Galicia",
    "Orense":     "Galicia",
    "Pontevedra": "Galicia",
    # Madrid
    "Madrid":     "Comunidad de Madrid",
    # Murcia
    "Murcia":     "Región de Murcia",
    # Navarra
    "Navarra":    "Navarra",
    # País Vasco
    "Álava":      "País Vasco",
    "Gipúzkoa":   "País Vasco",
    "Vizcaya":    "País Vasco",
    # La Rioja
    "La Rioja":   "La Rioja",
    # Special territories (assigned to nearest zone for routing)
    "Ceuta":      "Ceuta",
    "Melilla":    "Melilla",
    "Andorra":    "Andorra",   # not Spain — treated as East for routing
}

# =============================================================================
# CCAA → COMMERCIAL ZONE
# =============================================================================
# Zones as requested:
#   north   : Galicia, Asturias, Cantabria, Castilla y León, La Rioja, Navarra, País Vasco
#   east    : Aragón, Cataluña, Comunitat Valenciana, Región de Murcia
#   south   : Comunidad de Madrid, Castilla-La Mancha, Andalucía, Extremadura
#   canary  : Canarias
#   balearic: Illes Balears

CCAA_TO_ZONE: dict[str, str] = {
    "Galicia":              "north",
    "Asturias":             "north",
    "Cantabria":            "north",
    "Castilla y León":      "north",
    "La Rioja":             "north",
    "Navarra":              "north",
    "País Vasco":           "north",
    "Aragón":               "east",
    "Cataluña":             "east",
    "Comunitat Valenciana": "east",
    "Región de Murcia":     "east",
    "Andorra":              "east",   # routed to east for demo
    "Comunidad de Madrid":  "south",
    "Castilla-La Mancha":   "south",
    "Andalucía":            "south",
    "Extremadura":          "south",
    "Ceuta":                "south",
    "Melilla":              "south",
    "Canarias":             "canary",
    "Illes Balears":        "balearic",
}

# =============================================================================
# ZONE → AGENT IDs
# Each zone has a list of agent IDs. A client is assigned an agent
# deterministically via: agent_list[client_id % len(agent_list)]
# =============================================================================

ZONE_AGENTS: dict[str, list[int]] = {
    "north":    [1, 2, 3],
    "east":     [4, 5, 6],
    "south":    [7, 8, 9],
    "canary":   [10, 11, 12],
    "balearic": [13],
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def classify_client_value(total_spend: float, p25: float, p75: float) -> str:
    """Return Alto / Medio / Bajo based on spend percentiles."""
    if total_spend >= p75:
        return "Alto"
    if total_spend <= p25:
        return "Bajo"
    return "Medio"


def compute_alert_score(risk_percentile: float, propensity: float, value_class: str) -> float:
    """
    Combined priority score (used for SORTING alerts, not for filtering).
    Higher = surface first. Uses risk_percentile (0-100, uniform) rather than
    the raw score_riesgo_0_100 to avoid border clustering.
    """
    mult = VALUE_MULTIPLIERS.get(value_class, 0.5)
    return risk_percentile * (1.0 + propensity / 100.0) * mult


def get_risk_threshold(value_class: str) -> float:
    """Return minimum risk PERCENTILE required to trigger an alert for this tier."""
    return {
        "Alto":  RISK_THRESHOLD_ALTO,
        "Medio": RISK_THRESHOLD_MEDIO,
        "Bajo":  RISK_THRESHOLD_BAJO,
    }.get(value_class, RISK_THRESHOLD_BAJO)


def assign_risk_level(risk_percentile: float, propensity: float, client_value: str) -> str:
    """
    Alert risk label based on a composite of churn risk PERCENTILE, purchase
    propensity, and client value tier.

    Composite formula (0–100 scale):
      50% weight → risk_percentile  (uniform 0-100 rank within candidate set)
      30% weight → score_potencial
      20% weight → client value tier (Alto=100, Medio=60, Bajo=25)

    Thresholds:
      composite ≥ HIGH_ALERT_RISK_THRESHOLD   → "Alto"
      composite ≥ MEDIUM_ALERT_RISK_THRESHOLD  → "Medio"
      else                                      → "Bajo"
    """
    value_score = {"Alto": 100.0, "Medio": 60.0, "Bajo": 25.0}.get(client_value, 50.0)
    composite = risk_percentile * 0.50 + propensity * 0.30 + value_score * 0.20
    if composite >= HIGH_ALERT_RISK_THRESHOLD:
        return "Alto"
    if composite >= MEDIUM_ALERT_RISK_THRESHOLD:
        return "Medio"
    return "Bajo"


def get_ccaa(provincia: str) -> str:
    if pd.isna(provincia):
        return "Desconocida"
    return PROVINCIA_TO_CCAA.get(str(provincia).strip(), "Desconocida")


def get_zone(ccaa: str) -> str:
    return CCAA_TO_ZONE.get(ccaa, "south")  # default to south if unknown


def get_agent_id(client_id: int, zone: str) -> int:
    agents = ZONE_AGENTS.get(zone, [7])
    return agents[client_id % len(agents)]


def build_explanation(row: pd.Series, alert_type: str) -> str:
    """
    Generate a plain-language explanation of why this alert was triggered.
    Uses fields available in the latest prediction row.
    """
    parts = []

    # Purchase timing context
    avg_days = row.get("tiempo_medio_recompra_dias", None)
    days_since = row.get("dias_desde_compra_anterior_producto", None)
    if pd.notna(avg_days) and pd.notna(days_since) and avg_days > 0:
        overdue = days_since - avg_days
        if overdue > 0:
            parts.append(
                f"La darrera compra d'aquest producte va ser fa {int(days_since)} dies "
                f"(mitjana habitual: {int(avg_days)} dies, retard de {int(overdue)} dies)."
            )
        else:
            parts.append(
                f"La darrera compra va ser fa {int(days_since)} dies "
                f"(dins la seva freqüència habitual de {int(avg_days)} dies)."
            )

    # Spend context
    gasto_real = row.get("gasto_anual_real_cliente_producto", None)
    gasto_esperado = row.get("gasto_medio_anual_cliente_categoria_producto", None)
    if pd.notna(gasto_real) and pd.notna(gasto_esperado) and gasto_esperado > 0:
        ratio = gasto_real / gasto_esperado
        pct = int(round(ratio * 100))
        if pct < 80:
            parts.append(
                f"La despesa anual real en aquest producte ({gasto_real:.0f}€) "
                f"és un {100 - pct}% inferior a la mitjana esperada ({gasto_esperado:.0f}€)."
            )
        elif pct > 120:
            parts.append(
                f"La despesa anual real ({gasto_real:.0f}€) supera la mitjana "
                f"esperada ({gasto_esperado:.0f}€) en un {pct - 100}%."
            )

    # Propensity context
    propensity = row.get("score_potencial_0_100", None)
    if pd.notna(propensity):
        if propensity >= 60:
            parts.append(
                f"La propensió de compra és alta ({propensity:.0f}/100), "
                "cosa que suggereix que el client continua actiu en el mercat."
            )
        else:
            parts.append(
                f"La propensió de compra és baixa ({propensity:.0f}/100), "
                "cosa que indica una reducció de l'activitat compradora general."
            )

    # Alert type context
    if alert_type == "Total":
        parts.append(
            "El risc afecta múltiples línies de producte, "
            "la qual cosa apunta a un canvi global en la relació comercial."
        )
    elif alert_type == "Combinat":
        parts.append(
            "El risc afecta diverses línies de producte, "
            "indicant una reducció parcial de la relació comercial."
        )

    return " ".join(parts) if parts else "Alerta basada en risc de fuga i propensió de compra."


def make_alert_id(client_id: int, product_id, seq: int) -> str:
    """Generate a short stable alert ID."""
    key = f"{client_id}-{product_id}-{seq}"
    return "ALT-" + hashlib.md5(key.encode()).hexdigest()[:8].upper()


# =============================================================================
# MAIN PIPELINE
# =============================================================================

def run_pipeline(input_csv: str, output_csv: str) -> None:
    print(f"[1/8] Loading {input_csv}…")
    df = pd.read_csv(input_csv)
    print(f"      {len(df):,} rows, {df['Id. Cliente'].nunique():,} clients, "
          f"{df['Id. Producto'].nunique()} products")
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")

    # ── Step 1: Compute temporal inference window ───────────────────────────
    print("[2/8] Computing temporal inference window…")
    reference_date = df["Fecha"].max()
    window_end   = reference_date - pd.DateOffset(months=RECENCY_EXCLUSION_MONTHS)
    window_start = reference_date - pd.DateOffset(months=LOOKBACK_MONTHS)
    print(f"      Reference date (latest buy in dataset): {reference_date.date()}")
    print(f"      Window: {window_start.date()} → {window_end.date()}")
    print(f"      (Excluding last {RECENCY_EXCLUSION_MONTHS} months; "
          f"max staleness {LOOKBACK_MONTHS} months)")

    df_window = df[(df["Fecha"] >= window_start) & (df["Fecha"] <= window_end)].copy()
    print(f"      Rows within window: {len(df_window):,}  "
          f"({df_window['Id. Cliente'].nunique():,} clients, "
          f"{df_window['Id. Producto'].nunique()} products)")

    # ── Step 2: Latest row per (client, product) within the window ──────────
    print("[3/8] Selecting latest prediction per (client, product) in window…")
    latest = (
        df_window.sort_values("Fecha")
                 .groupby(["Id. Cliente", "Id. Producto"], as_index=False)
                 .last()
    )
    print(f"      {len(latest):,} (client, product) combos")

    # ── Step 3: Client value classification ─────────────────────────────────
    # Use FULL history (not just the window) for spend classification, so that
    # a client's long-term value is not distorted by the window cutoff.
    print("[4/8] Classifying client value (Alto / Medio / Bajo) from full history…")
    client_spend = df.groupby("Id. Cliente")["Valores_H"].sum().rename("total_spend")
    p25 = client_spend.quantile(CLIENT_VALUE_LOW_PERCENTILE)
    p75 = client_spend.quantile(CLIENT_VALUE_HIGH_PERCENTILE)
    print(f"      Spend percentiles — P25: {p25:,.0f}€  P75: {p75:,.0f}€")

    latest = latest.merge(client_spend, on="Id. Cliente", how="left")
    latest["client_value"] = latest["total_spend"].apply(
        lambda s: classify_client_value(s, p25, p75)
    )

    # ── Step 3b: Percentile-rank the risk score ──────────────────────────────
    # Replace raw score_riesgo_0_100 with its percentile rank within the
    # candidate universe so scores are uniformly distributed across 0-100
    # and not clustered at the high end.
    print("[4b] Computing risk percentile ranks within window candidates…")
    latest["risk_percentile"] = latest["score_riesgo_0_100"].rank(pct=True) * 100
    print(f"      risk_percentile distribution — "
          f"P25: {latest['risk_percentile'].quantile(0.25):.1f}  "
          f"P50: {latest['risk_percentile'].quantile(0.50):.1f}  "
          f"P75: {latest['risk_percentile'].quantile(0.75):.1f}  "
          f"P90: {latest['risk_percentile'].quantile(0.90):.1f}")

    # ── Step 3c: Percentile-rank the propensity score ────────────────────────
    # Applies the same treatment as risk: raw score_potencial_0_100 also
    # clusters at 87–99, so replacing it with its percentile rank ensures
    # displayed propensity values have meaningful spread.
    print("[4c] Computing propensity percentile ranks within window candidates…")
    latest["propensity_percentile"] = latest["score_potencial_0_100"].rank(pct=True) * 100
    print(f"      propensity_percentile distribution — "
          f"P25: {latest['propensity_percentile'].quantile(0.25):.1f}  "
          f"P50: {latest['propensity_percentile'].quantile(0.50):.1f}  "
          f"P75: {latest['propensity_percentile'].quantile(0.75):.1f}  "
          f"P90: {latest['propensity_percentile'].quantile(0.90):.1f}")

    # ── Step 4: Per-tier alert scoring & filtering ───────────────────────────
    print("[5/8] Filtering candidates with per-tier risk thresholds…")
    latest["alert_score"] = latest.apply(
        lambda r: compute_alert_score(
            r["risk_percentile"],
            r["propensity_percentile"],
            r["client_value"],
        ),
        axis=1,
    )
    # Apply per-tier risk threshold using percentile rank (and optional propensity filter)
    latest["_tier_threshold"] = latest["client_value"].apply(get_risk_threshold)
    candidates = latest[
        (latest["risk_percentile"] >= latest["_tier_threshold"]) &
        (latest["score_potencial_0_100"] >= MIN_PROPENSITY_THRESHOLD)
    ].copy()
    for tier in ["Alto", "Medio", "Bajo"]:
        n = (candidates["client_value"] == tier).sum()
        thr = get_risk_threshold(tier)
        print(f"      {tier}: {n:,} pairs (risk_percentile≥{thr})")

    # ── Step 5: Zone + agent ─────────────────────────────────────────────────
    print("[6/8] Mapping province → CCAA → zone → agent…")
    client_provincia = (
        df_window.sort_values("Fecha")
                 .groupby("Id. Cliente")["Provincia"]
                 .last()
                 .rename("provincia_latest")
    )
    candidates = candidates.merge(client_provincia, on="Id. Cliente", how="left")
    candidates["provincia_used"] = candidates["Provincia"].fillna(
        candidates["provincia_latest"]
    )
    candidates["comunidad_autonoma"] = candidates["provincia_used"].apply(get_ccaa)
    candidates["zone"] = candidates["comunidad_autonoma"].apply(get_zone)
    candidates["agent_id"] = candidates.apply(
        lambda r: get_agent_id(int(r["Id. Cliente"]), r["zone"]), axis=1
    )

    # ── Step 6: Decide alert type per client ─────────────────────────────────
    print("[7/8] Deciding alert type (Total / Combinat / Producto X) per client…")
    records = []

    for client_id, group in candidates.groupby("Id. Cliente"):
        group = group.sort_values("alert_score", ascending=False)
        n_products = len(group)

        # Pick the row with the highest alert_score as the "representative" row
        rep = group.iloc[0]
        provincia = rep["provincia_used"] if pd.notna(rep["provincia_used"]) else "Desconocida"
        ccaa = rep["comunidad_autonoma"]
        zone = rep["zone"]
        agent_id = rep["agent_id"]
        client_value = rep["client_value"]
        client_name = get_client_name(int(client_id))

        if n_products >= MULTI_PRODUCT_THRESHOLD:
            # ── TOTAL alert — use average risk percentile/propensity across products
            avg_risk_pct = group["risk_percentile"].mean()
            avg_prop_pct = group["propensity_percentile"].mean()
            risk_level = assign_risk_level(avg_risk_pct, avg_prop_pct, client_value)
            product_list = sorted(group["Id. Producto"].astype(str).tolist())
            explanation = build_explanation(rep, "Total")
            rec = {
                "alert_id":               make_alert_id(int(client_id), "total", 0),
                "client_id":              int(client_id),
                "client_name":            client_name,
                "provincia":              provincia,
                "comunidad_autonoma":     ccaa,
                "zone":                   zone,
                "agent_id":               agent_id,
                "product_id":             "Total",
                "alert_type":             "Total",
                "risk_level":             risk_level,
                "client_value":           client_value,
                "churn_probability":      round(avg_risk_pct, 2),
                "purchase_propensity":    round(avg_prop_pct, 2),
                "predicted_next_purchase": rep["prediccion_fecha_proxima_compra"],
                "last_order_date":        rep["Fecha"].strftime("%Y-%m-%d")
                                          if pd.notna(rep["Fecha"]) else None,
                "alert_score":            round(rep["alert_score"], 2),
                "explanation":            explanation,
                # Context fields for LLM
                "ctx_productos_afectados":   ", ".join(product_list),
                "ctx_n_productos":           n_products,
                "ctx_gasto_anual_real":      round(rep.get("gasto_anual_real_cliente_producto", 0) or 0, 2),
                "ctx_gasto_esperado":        round(rep.get("gasto_medio_anual_cliente_categoria_producto", 0) or 0, 2),
                "ctx_dias_desde_compra":     rep.get("dias_desde_compra_anterior_producto", None),
                "ctx_tiempo_medio_recompra": rep.get("tiempo_medio_recompra_dias", None),
                "ctx_zscore_momento":        round(rep.get("zscore_momento_cliente_producto", 0) or 0, 3),
                "ctx_potencial_clase":       rep.get("potencial_clase_predicha", None),
                "ctx_num_compras_anteriores": rep.get("numero_compras_anteriores_producto", None),
                "ctx_total_compras_otros":   rep.get("total_compras_cliente_otros_productos", None),
                "ctx_vuelve_a_comprar":      rep.get("vuelve_a_comprar", None),
            }
            records.append(rec)

        elif n_products >= COMBINED_ALERT_MIN_PRODUCTS:
            # ── COMBINED alert — 2+ products but below Total threshold ──
            # Collapse into a single alert to avoid flooding the dashboard.
            avg_risk_pct = group["risk_percentile"].mean()
            avg_prop_pct = group["propensity_percentile"].mean()
            risk_level = assign_risk_level(avg_risk_pct, avg_prop_pct, client_value)
            product_list = sorted(group["Id. Producto"].astype(str).tolist())
            alert_type = "Combinat"
            explanation = build_explanation(rep, "Combinat")
            rec = {
                "alert_id":               make_alert_id(int(client_id), "combined", 0),
                "client_id":              int(client_id),
                "client_name":            client_name,
                "provincia":              provincia,
                "comunidad_autonoma":     ccaa,
                "zone":                   zone,
                "agent_id":               agent_id,
                "product_id":             "Combinat",
                "alert_type":             alert_type,
                "risk_level":             risk_level,
                "client_value":           client_value,
                "churn_probability":      round(avg_risk_pct, 2),
                "purchase_propensity":    round(avg_prop_pct, 2),
                "predicted_next_purchase": rep["prediccion_fecha_proxima_compra"],
                "last_order_date":        rep["Fecha"].strftime("%Y-%m-%d")
                                          if pd.notna(rep["Fecha"]) else None,
                "alert_score":            round(rep["alert_score"], 2),
                "explanation":            explanation,
                # Context fields for LLM
                "ctx_productos_afectados":   ", ".join(product_list),
                "ctx_n_productos":           n_products,
                "ctx_gasto_anual_real":      round(rep.get("gasto_anual_real_cliente_producto", 0) or 0, 2),
                "ctx_gasto_esperado":        round(rep.get("gasto_medio_anual_cliente_categoria_producto", 0) or 0, 2),
                "ctx_dias_desde_compra":     rep.get("dias_desde_compra_anterior_producto", None),
                "ctx_tiempo_medio_recompra": rep.get("tiempo_medio_recompra_dias", None),
                "ctx_zscore_momento":        round(rep.get("zscore_momento_cliente_producto", 0) or 0, 3),
                "ctx_potencial_clase":       rep.get("potencial_clase_predicha", None),
                "ctx_num_compras_anteriores": rep.get("numero_compras_anteriores_producto", None),
                "ctx_total_compras_otros":   rep.get("total_compras_cliente_otros_productos", None),
                "ctx_vuelve_a_comprar":      rep.get("vuelve_a_comprar", None),
            }
            records.append(rec)

        else:
            # ── PER-PRODUCT alert — only 1 product triggering ──
            row = group.iloc[0]
            product_id = row["Id. Producto"]
            risk_level = assign_risk_level(
                row["risk_percentile"],
                row["propensity_percentile"],
                client_value,
            )
            explanation = build_explanation(row, f"Producto {product_id}")
            rec = {
                "alert_id":               make_alert_id(int(client_id), product_id, 0),
                "client_id":              int(client_id),
                "client_name":            client_name,
                "provincia":              provincia,
                "comunidad_autonoma":     ccaa,
                "zone":                   zone,
                "agent_id":               agent_id,
                "product_id":             int(product_id),
                "alert_type":             f"Producto {product_id}",
                "risk_level":             risk_level,
                "client_value":           client_value,
                "churn_probability":      round(row["risk_percentile"], 2),
                "purchase_propensity":    round(row["propensity_percentile"], 2),
                "predicted_next_purchase": row["prediccion_fecha_proxima_compra"],
                "last_order_date":        row["Fecha"].strftime("%Y-%m-%d")
                                          if pd.notna(row["Fecha"]) else None,
                "alert_score":            round(row["alert_score"], 2),
                "explanation":            explanation,
                # Context fields for LLM
                "ctx_productos_afectados":   str(product_id),
                "ctx_n_productos":           1,
                "ctx_gasto_anual_real":      round(row.get("gasto_anual_real_cliente_producto", 0) or 0, 2),
                "ctx_gasto_esperado":        round(row.get("gasto_medio_anual_cliente_categoria_producto", 0) or 0, 2),
                "ctx_dias_desde_compra":     row.get("dias_desde_compra_anterior_producto", None),
                "ctx_tiempo_medio_recompra": row.get("tiempo_medio_recompra_dias", None),
                "ctx_zscore_momento":        round(row.get("zscore_momento_cliente_producto", 0) or 0, 3),
                "ctx_potencial_clase":       row.get("potencial_clase_predicha", None),
                "ctx_num_compras_anteriores": row.get("numero_compras_anteriores_producto", None),
                "ctx_total_compras_otros":   row.get("total_compras_cliente_otros_productos", None),
                "ctx_vuelve_a_comprar":      row.get("vuelve_a_comprar", None),
            }
            records.append(rec)

    alerts_df = pd.DataFrame(records)
    print(f"      Generated {len(alerts_df):,} raw alerts")

    # ── Step 6: Sort by priority and apply per-tier caps ────────────────────
    alerts_df = alerts_df.sort_values("alert_score", ascending=False)

    tier_caps = {"Alto": MAX_ALERTS_ALTO, "Medio": MAX_ALERTS_MEDIO, "Bajo": MAX_ALERTS_BAJO}
    capped_parts = []
    for tier, cap in tier_caps.items():
        tier_df = alerts_df[alerts_df["client_value"] == tier].head(cap)
        capped_parts.append(tier_df)
        print(f"      {tier}: {len(tier_df):,} alerts (cap={cap})")
    alerts_df = pd.concat(capped_parts, ignore_index=True)

    # ── Step 6b: Assign risk levels by within-set percentile ────────────────
    # Use alert_score rank within the FINAL capped set so every agent's list
    # has a realistic mix of Alto / Medio / Bajo regardless of absolute values.
    print("[6b] Assigning risk levels by within-alert-set percentile of alert_score…")
    n_total  = len(alerts_df)
    n_high   = max(1, int(round(n_total * RISK_LEVEL_HIGH_PCT)))
    n_medium = max(1, int(round(n_total * RISK_LEVEL_MEDIUM_PCT)))
    alerts_df = alerts_df.sort_values("alert_score", ascending=False).reset_index(drop=True)
    alerts_df["risk_level"] = "Bajo"
    alerts_df.loc[:n_high - 1, "risk_level"] = "Alto"
    alerts_df.loc[n_high: n_high + n_medium - 1, "risk_level"] = "Medio"
    print(f"      Alto: {(alerts_df['risk_level']=='Alto').sum()}  "
          f"Medio: {(alerts_df['risk_level']=='Medio').sum()}  "
          f"Bajo: {(alerts_df['risk_level']=='Bajo').sum()}")

    # ── Step 6c: Rescale churn_probability and purchase_propensity ──────────
    # Min-max scale within the final set so displayed values span a human-readable
    # range instead of clustering at 95-100%. Preserves relative ordering.
    print("[6c] Rescaling churn_probability and purchase_propensity for display…")

    def minmax_rescale(series: pd.Series, lo: float, hi: float) -> pd.Series:
        s_min, s_max = series.min(), series.max()
        if s_max == s_min:
            return series.apply(lambda _: round((lo + hi) / 2, 2))
        return ((series - s_min) / (s_max - s_min) * (hi - lo) + lo).round(2)

    alerts_df["churn_probability"]   = minmax_rescale(
        alerts_df["churn_probability"],   DISPLAY_SCORE_MIN,      DISPLAY_SCORE_MAX)
    alerts_df["purchase_propensity"] = minmax_rescale(
        alerts_df["purchase_propensity"], DISPLAY_PROPENSITY_MIN, DISPLAY_PROPENSITY_MAX)

    print(f"      churn_probability   — min: {alerts_df['churn_probability'].min():.1f}  "
          f"max: {alerts_df['churn_probability'].max():.1f}  "
          f"mean: {alerts_df['churn_probability'].mean():.1f}  "
          f"std: {alerts_df['churn_probability'].std():.1f}")
    print(f"      purchase_propensity — min: {alerts_df['purchase_propensity'].min():.1f}  "
          f"max: {alerts_df['purchase_propensity'].max():.1f}  "
          f"mean: {alerts_df['purchase_propensity'].mean():.1f}  "
          f"std: {alerts_df['purchase_propensity'].std():.1f}")

    # Final sort: risk level first, then alert_score (priority within tier)
    risk_order = {"Alto": 0, "Medio": 1, "Bajo": 2}
    alerts_df["_risk_sort"] = alerts_df["risk_level"].map(risk_order)
    alerts_df = alerts_df.sort_values(
        ["_risk_sort", "alert_score"],
        ascending=[True, False],
    ).drop(columns=["_risk_sort"])

    # ── Step 7: Write output ─────────────────────────────────────────────────
    # Attach the window metadata as informational columns for downstream tools.
    alerts_df["inference_reference_date"] = reference_date.date().isoformat()
    alerts_df["inference_window_start"]   = window_start.date().isoformat()
    alerts_df["inference_window_end"]     = window_end.date().isoformat()

    print(f"[8/8] Writing {output_csv}…")
    alerts_df.to_csv(output_csv, index=False, encoding="utf-8-sig")

    # ── Summary ──────────────────────────────────────────────────────────────
    print("\n── Summary ─────────────────────────────────────────────────")
    print(f"  Reference date:     {reference_date.date()}  "
          f"(window {window_start.date()} → {window_end.date()})")
    print(f"  Total alerts:       {len(alerts_df)}")
    print(f"  By type:")
    for atype, cnt in alerts_df["alert_type"].value_counts().head(10).items():
        print(f"    {atype:<20} {cnt}")
    print(f"  By risk level:      {alerts_df['risk_level'].value_counts().to_dict()}")
    print(f"  By client value:    {alerts_df['client_value'].value_counts().to_dict()}")
    print(f"  By zone:            {alerts_df['zone'].value_counts().to_dict()}")
    print(f"  By agent_id:        {alerts_df['agent_id'].value_counts().sort_index().to_dict()}")
    print(f"  Output:             {os.path.abspath(output_csv)}")
    print("────────────────────────────────────────────────────────────\n")


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_csv  = os.path.join(script_dir, "predicciones.csv")
    output_csv = os.path.join(script_dir, "alerts.csv")
    run_pipeline(input_csv, output_csv)
