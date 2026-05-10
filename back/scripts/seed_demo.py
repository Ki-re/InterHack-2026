#!/usr/bin/env python3
"""
seed_demo.py
============
Injects synthetic interaction history into a random but deterministic
subset of alerts in the SQLite database, so the demo dashboard shows
realistic commercial activity (calls, visits, emails, dismissals).

Safe to re-run: already-seeded alerts are skipped.

Usage (inside the backend container / local venv):
    python scripts/seed_demo.py               # auto-detects DB
    python scripts/seed_demo.py /path/to.db   # explicit path

Detection order:
    1. CLI argument
    2. DATABASE_URL env var  (sqlite:///./app.db  →  ./app.db)
    3. Default: /app/app.db  (path inside Docker container)
"""

import json
import os
import random
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta, timezone

# ─────────────────────────────────────────────────────────────────────────────
# TUNEABLE PARAMETERS
# ─────────────────────────────────────────────────────────────────────────────

SEED = 42  # fixed RNG seed — keeps results stable across restarts

# Fraction of ALL alerts that become "attended" (with rich interaction history)
FRAC_ATTENDED = 0.30

# Fraction that become "dismissed" (with interactions + dismiss reason)
FRAC_DISMISSED = 0.08

# Fraction that remain "pending" but have ≥1 failed contact attempt recorded
FRAC_TOUCHED_PENDING = 0.22

# Remainder (1 - above) → pure pending, no interactions at all
# Currently ≈ 0.40 of alerts

# Max interaction records per alert (attended ones may have up to this many)
MAX_INTERACTIONS_ATTENDED  = 3
MAX_INTERACTIONS_DISMISSED = 2
MAX_INTERACTIONS_TOUCHED   = 2

# Base datetime for synthetic timestamps (latest possible interaction "today")
BASE_DT = datetime(2026, 4, 28, 17, 0, 0, tzinfo=timezone.utc)

# ─────────────────────────────────────────────────────────────────────────────
# COPY BANK  (bilingual ES/CA, dental-industry context)
# ─────────────────────────────────────────────────────────────────────────────

_PHONE_UNANSWERED = [
    "No contesta. Segundo intento previsto para mañana.",
    "Buzón de voz. Dejado mensaje con datos de contacto.",
    "No hi havia resposta. Es tornarà a intentar la setmana que ve.",
    "No disponible. Se intentará nuevamente por la tarde.",
    "Truca i no contesta. Possible baixa d'activitat a la clínica.",
]

_PHONE_POSITIVE = [
    "Confirmado interés en retomar pedidos de material de composite. Enviamos catálogo actualizado.",
    "Contacte positiu. Interessat en les novetats de la gama de restauració.",
    "Confirmó pedido grande previsto para el próximo mes. Muy receptivo.",
    "Molt bona disposició. Farà la comanda a finals de setmana.",
    "Han cambiado al responsable de compras. El nuevo contacto es favorable al acuerdo.",
]

_PHONE_NEUTRAL = [
    "Reconoce la bajada de pedidos. Comenta problemas de liquidez temporal. Sigue siendo cliente activo.",
    "Receptiu però no pren decisions fins la propera reunió de la clínica.",
    "Mucho trabajo en la clínica, pide que le contactemos en 2 semanas.",
    "Situació econòmica complicada. No descarta reprendre les comandes.",
    "Interés moderado. Necesita comparar precios con otro proveedor antes de decidir.",
]

_PHONE_NEGATIVE = [
    "No está interesado. Trabajan ya con otro proveedor y están satisfechos.",
    "La clínica ha reduït les activitats. Poc potencial a curt termini.",
    "Han encontrado un proveedor con mejores precios. Precio es el factor clave.",
    "No vol canviar de proveïdor. Relació consolidada amb la competència.",
    "Clínica en proceso de cierre. No hay perspectiva de pedido.",
]

_VISIT_SUCCESSFUL_POSITIVE = [
    "Visita exitosa. Presentación de nuevos materiales de ortodoncia con muy buena acogida. Pedido en 10 días.",
    "Visita molt positiva. Hem tancat un compromís de comanda per al mes vinent.",
    "Revisada toda la cartera de materiales. Pedido confirmado para fin de mes.",
    "El dentista ha mostrado especial interés en los materiales de endodoncia. Demostración programada.",
    "Visita productiva. Acuerdo marco para aprovisionamiento trimestral.",
]

_VISIT_SUCCESSFUL_NEUTRAL = [
    "Visita realizada. Interés moderado. Están evaluando proveedores.",
    "Visita completada. Comentan reducción de actividad pero no descartan reanudar.",
    "Han rebut la visita. Estan en procés de negociació amb la central de la clínica.",
    "Visita neutra. Piden más tiempo antes de tomar una decisión.",
    "Recepción cordial pero sin compromiso. Se programará seguimiento en un mes.",
]

_VISIT_UNSUCCESSFUL = [
    "La clínica estaba cerrada. Se intenta nueva visita la próxima semana.",
    "No estava el responsable de compres. Es deixa catàleg i es concorda nova visita.",
    "Visita fallida por reunión interna. Reprogramada para la próxima semana.",
    "El dentista estaba en intervención. Se dejó tarjeta y muestra de producto.",
    "Clínica tancada per vacances. Es tornarà a contactar al setembre.",
]

_EMAIL_RESPONDED_POSITIVE = [
    "Respuesta positiva. Solicitan propuesta comercial con precio de volumen.",
    "Han contestat per email. Interessats i demanen preus actualitzats.",
    "Replied positively. Request for updated catalog for restoration materials.",
    "Resposta favorable. Volen rebre visita del delegat la setmana que ve.",
    "Respuesta rápida. Confirman que retoman el nivel de pedidos anterior.",
]

_EMAIL_RESPONDED_NEUTRAL = [
    "Respuesta recibida. Piden más tiempo para decidir.",
    "Resposta rebuda. Ho consultaran amb la direcció de la clínica.",
    "Replied asking for more information on pricing and delivery times.",
    "Contesten però sense compromís clar. Seguiment previst.",
    "Han respondido. Evalúan la propuesta y responderán en 2 semanas.",
]

_EMAIL_NOT_RESPONDED = [
    "Email enviado con propuesta. Sin respuesta tras 3 días hábiles.",
    "Enviado email de seguimiento. Sense resposta de moment.",
    "Seguimiento por email enviado. Pendiente de respuesta.",
    "Segon email enviat. Sense confirmació de recepció.",
    "Email con catálogo adjunto. Sin acuse de recibo.",
]

_DISMISS_REASONS = [
    "La clínica ha fet un concurs de creditors. No facturable a curt termini.",
    "Client ha tancat la clínica temporalment per reforma. Revisió prevista en 6 mesos.",
    "Conflicte de preus no resoluble. El client prefereix un proveïdor local.",
    "Han centralizado las compras en una sede diferente. No corresponde a este delegado.",
    "El dentista principal s'ha jubilat i la clínica ha tancat definitivament.",
    "Client irrecuperable — canvi de proveïdor definitiu confirmat per escrit.",
    "Clínica cerrada por vacaciones hasta el 1 de septiembre.",
    "Comprador ha canviat. Nou contacte pendent d'identificar per la nova direcció.",
    "Baixa d'activitat per reforma de local. No hi ha previsió de compra en 4 mesos.",
    "Han firmado exclusividad con otro distribuidor. Sin margen de negociación.",
]

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _uid() -> str:
    return str(uuid.uuid4())


def _ts(days_ago: float, hour_offset: float = 0.0) -> str:
    dt = BASE_DT - timedelta(days=days_ago, hours=hour_offset)
    return dt.isoformat()


def _pick(rng: random.Random, lst: list) -> str:
    return rng.choice(lst)


def _phone_interaction(rng: random.Random, days_ago: float, allow_positive: bool = True) -> dict:
    answered = rng.random() > 0.4
    rec: dict = {
        "id": _uid(),
        "handledBy": "phone",
        "answered": answered,
        "keepOpen": True,
        "submittedAt": _ts(days_ago),
    }
    if answered:
        if allow_positive:
            result = rng.choices(["positive", "neutral", "negative"], weights=[45, 35, 20])[0]
        else:
            result = rng.choices(["neutral", "negative"], weights=[50, 50])[0]
        rec["result"] = result
        if result == "positive":
            rec["notes"] = _pick(rng, _PHONE_POSITIVE)
        elif result == "neutral":
            rec["notes"] = _pick(rng, _PHONE_NEUTRAL)
        else:
            rec["notes"] = _pick(rng, _PHONE_NEGATIVE)
    else:
        rec["notes"] = _pick(rng, _PHONE_UNANSWERED)
    return rec


def _visit_interaction(rng: random.Random, days_ago: float, allow_positive: bool = True) -> dict:
    successful = rng.random() > 0.35
    rec: dict = {
        "id": _uid(),
        "handledBy": "visit",
        "visitSuccessful": successful,
        "keepOpen": True,
        "submittedAt": _ts(days_ago),
    }
    if successful:
        if allow_positive:
            result = rng.choices(["positive", "neutral"], weights=[65, 35])[0]
        else:
            result = "neutral"
        rec["result"] = result
        if result == "positive":
            rec["notes"] = _pick(rng, _VISIT_SUCCESSFUL_POSITIVE)
        else:
            rec["notes"] = _pick(rng, _VISIT_SUCCESSFUL_NEUTRAL)
    else:
        rec["notes"] = _pick(rng, _VISIT_UNSUCCESSFUL)
    return rec


def _email_interaction(rng: random.Random, days_ago: float, allow_positive: bool = True) -> dict:
    responded = rng.random() > 0.55
    rec: dict = {
        "id": _uid(),
        "handledBy": "email",
        "emailResponseReceived": responded,
        "keepOpen": True,
        "submittedAt": _ts(days_ago),
    }
    if responded:
        if allow_positive:
            result = rng.choices(["positive", "neutral"], weights=[55, 45])[0]
        else:
            result = "neutral"
        rec["result"] = result
        if result == "positive":
            rec["notes"] = _pick(rng, _EMAIL_RESPONDED_POSITIVE)
        else:
            rec["notes"] = _pick(rng, _EMAIL_RESPONDED_NEUTRAL)
    else:
        rec["notes"] = _pick(rng, _EMAIL_NOT_RESPONDED)
    return rec


def _random_interaction(rng: random.Random, days_ago: float, allow_positive: bool = True) -> dict:
    channel = rng.choices(["phone", "visit", "email"], weights=[50, 30, 20])[0]
    if channel == "phone":
        return _phone_interaction(rng, days_ago, allow_positive)
    if channel == "visit":
        return _visit_interaction(rng, days_ago, allow_positive)
    return _email_interaction(rng, days_ago, allow_positive)


def _build_attended_history(rng: random.Random) -> tuple[list, list, str]:
    """
    Returns (interactions, events, attended_at_iso).
    Builds 1-3 interactions leading to a successful closure.
    The last interaction has keepOpen=False.
    """
    n = rng.randint(1, MAX_INTERACTIONS_ATTENDED)
    interactions = []
    # Space interactions across the past 30 days
    days_offsets = sorted(rng.sample(range(1, 31), min(n, 30)), reverse=True)

    for i, days_ago in enumerate(days_offsets):
        is_last = i == len(days_offsets) - 1
        rec = _random_interaction(rng, days_ago, allow_positive=True)
        if is_last:
            # Final interaction closes the alert — make it positive
            rec["result"] = "positive"
            rec["keepOpen"] = False
            if rec["handledBy"] == "phone":
                rec["answered"] = True
                rec["notes"] = _pick(rng, _PHONE_POSITIVE)
            elif rec["handledBy"] == "visit":
                rec["visitSuccessful"] = True
                rec["notes"] = _pick(rng, _VISIT_SUCCESSFUL_POSITIVE)
            else:
                rec["emailResponseReceived"] = True
                rec["notes"] = _pick(rng, _EMAIL_RESPONDED_POSITIVE)
        interactions.append(rec)

    attended_at = _ts(days_offsets[-1] - 0.1)  # just after final interaction
    closed_event = {
        "id": _uid(),
        "type": "closed",
        "timestamp": attended_at,
    }
    return interactions, [closed_event], attended_at


def _build_dismissed_history(rng: random.Random) -> tuple[list, list, str, str]:
    """
    Returns (interactions, events, dismissed_at_iso, dismiss_reason).
    1-2 interactions then dismiss.
    """
    n = rng.randint(1, MAX_INTERACTIONS_DISMISSED)
    days_offsets = sorted(rng.sample(range(2, 25), min(n, 23)), reverse=True)
    interactions = []
    for days_ago in days_offsets:
        rec = _random_interaction(rng, days_ago, allow_positive=False)
        interactions.append(rec)

    dismissed_at = _ts(days_offsets[-1] - 0.2)
    reason = _pick(rng, _DISMISS_REASONS)
    dismissed_event = {
        "id": _uid(),
        "type": "dismissed",
        "reason": reason,
        "timestamp": dismissed_at,
    }
    return interactions, [dismissed_event], dismissed_at, reason


def _build_touched_pending_history(rng: random.Random) -> tuple[list, list]:
    """
    Returns (interactions, events).
    1-2 failed contact attempts; alert remains pending.
    """
    n = rng.randint(1, MAX_INTERACTIONS_TOUCHED)
    days_offsets = sorted(rng.sample(range(1, 20), min(n, 19)), reverse=True)
    interactions = []
    for days_ago in days_offsets:
        # These should be failed contacts (unanswered phone, unsuccessful visit, no email reply)
        channel = rng.choices(["phone", "visit", "email"], weights=[55, 25, 20])[0]
        if channel == "phone":
            rec = {
                "id": _uid(),
                "handledBy": "phone",
                "answered": False,
                "keepOpen": True,
                "notes": _pick(rng, _PHONE_UNANSWERED),
                "submittedAt": _ts(days_ago),
            }
        elif channel == "visit":
            rec = {
                "id": _uid(),
                "handledBy": "visit",
                "visitSuccessful": False,
                "keepOpen": True,
                "notes": _pick(rng, _VISIT_UNSUCCESSFUL),
                "submittedAt": _ts(days_ago),
            }
        else:
            rec = {
                "id": _uid(),
                "handledBy": "email",
                "emailResponseReceived": False,
                "keepOpen": True,
                "notes": _pick(rng, _EMAIL_NOT_RESPONDED),
                "submittedAt": _ts(days_ago),
            }
        interactions.append(rec)
    return interactions, []


# ─────────────────────────────────────────────────────────────────────────────
# DB HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_db_path(argv: list[str]) -> str:
    if len(argv) > 1:
        return argv[1]
    raw = os.environ.get("DATABASE_URL", "")
    if raw.startswith("sqlite:///"):
        candidate = raw[len("sqlite:///"):]
        # Resolve relative path against /app (Docker working dir)
        if not os.path.isabs(candidate):
            candidate = os.path.join("/app", candidate.lstrip("./"))
        return candidate
    return "/app/app.db"


def _already_seeded(conn: sqlite3.Connection) -> bool:
    """Return True if >10 alerts already have interactions_json set."""
    try:
        cur = conn.execute(
            "SELECT COUNT(*) FROM regional_alerts WHERE interactions_json IS NOT NULL"
        )
        count = cur.fetchone()[0]
        return count > 10
    except sqlite3.OperationalError:
        # Column not added yet (migration not run) — can't seed yet.
        return True


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    db_path = _resolve_db_path(sys.argv)
    print(f"[seed_demo] DB: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    if _already_seeded(conn):
        print("[seed_demo] Already seeded — skipping.")
        conn.close()
        return

    # Load all alert IDs
    alert_ids: list[int] = [
        row["id"] for row in conn.execute("SELECT id FROM regional_alerts ORDER BY id").fetchall()
    ]
    total = len(alert_ids)
    print(f"[seed_demo] Found {total} alerts. Seeding…")

    rng = random.Random(SEED)
    rng.shuffle(alert_ids)  # deterministic shuffle

    n_attended  = int(total * FRAC_ATTENDED)
    n_dismissed = int(total * FRAC_DISMISSED)
    n_touched   = int(total * FRAC_TOUCHED_PENDING)

    attended_ids  = alert_ids[:n_attended]
    dismissed_ids = alert_ids[n_attended: n_attended + n_dismissed]
    touched_ids   = alert_ids[n_attended + n_dismissed: n_attended + n_dismissed + n_touched]
    # Remaining stay as pure pending

    updates: list[tuple] = []

    for aid in attended_ids:
        interactions, events, attended_at = _build_attended_history(rng)
        updates.append((
            json.dumps(interactions, ensure_ascii=False),
            json.dumps(events, ensure_ascii=False),
            "attended",
            attended_at,
            None,   # dismissed_at
            None,   # dismiss_reason
            aid,
        ))

    for aid in dismissed_ids:
        interactions, events, dismissed_at, reason = _build_dismissed_history(rng)
        updates.append((
            json.dumps(interactions, ensure_ascii=False),
            json.dumps(events, ensure_ascii=False),
            "dismissed",
            None,         # attended_at
            dismissed_at,
            reason,
            aid,
        ))

    for aid in touched_ids:
        interactions, events = _build_touched_pending_history(rng)
        updates.append((
            json.dumps(interactions, ensure_ascii=False),
            json.dumps(events, ensure_ascii=False),
            "pending",
            None,
            None,
            None,
            aid,
        ))

    conn.executemany(
        """
        UPDATE regional_alerts
        SET interactions_json = ?,
            events_json       = ?,
            status            = ?,
            attended_at       = ?,
            dismissed_at      = ?,
            dismiss_reason    = ?
        WHERE id = ?
        """,
        updates,
    )
    conn.commit()
    conn.close()

    print(
        f"[seed_demo] Done. "
        f"Attended={n_attended}  Dismissed={n_dismissed}  "
        f"Touched-pending={n_touched}  "
        f"Pure-pending={total - n_attended - n_dismissed - n_touched}"
    )


if __name__ == "__main__":
    main()
