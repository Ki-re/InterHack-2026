#!/usr/bin/env python3
"""
seed_demo.py
============
Injects synthetic interaction history into a random but deterministic
subset of alerts in the SQLite database, so the demo dashboard shows
realistic commercial activity (calls, visits, emails, dismissals).

All interaction and closure timestamps are computed RELATIVE to each
alert's own created_at (set by migration 0010_backdate_alerts to Mon-Wed
of the current week), so response times are always positive and
attended_at values are always in the past.

After the global seed, a targeted east-zone boost converts most remaining
pending east alerts to attended so that region scores look realistic.

Safe to re-run: already-seeded alerts are skipped (idempotent check).

Usage (inside the backend container / local venv):
    python scripts/seed_demo.py               # auto-detects DB
    python scripts/seed_demo.py /path/to.db   # explicit path

Detection order:
    1. CLI argument
    2. DATABASE_URL env var  (sqlite:///./app.db  ->  ./app.db)
    3. Default: /app/app.db  (path inside Docker container)
"""

import json
import os
import random
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# TUNEABLE PARAMETERS
# ---------------------------------------------------------------------------

SEED = 42  # fixed RNG seed for reproducibility

FRAC_ATTENDED       = 0.55  # fraction that become "attended"
FRAC_DISMISSED      = 0.12  # fraction that become "dismissed"
FRAC_TOUCHED_PENDING= 0.15  # fraction with failed contacts but still pending
# Remainder (~18%) -> pure pending, no interactions

MAX_INTERACTIONS_ATTENDED  = 3
MAX_INTERACTIONS_DISMISSED = 2
MAX_INTERACTIONS_TOUCHED   = 2

# Attended response window: uniform(MIN, MAX) hours after created_at.
# MAX is also capped at (now - created_at - 0.5h) so attended_at is
# always strictly in the past when the script runs.
RESPONSE_TIME_MIN_HOURS = 3.0
RESPONSE_TIME_MAX_HOURS = 115.0

# East-zone boost: keep at most this many east alerts as pending after boost.
EAST_PENDING_KEEP = 6

# ---------------------------------------------------------------------------
# COPY BANK  (bilingual ES/CA, dental-industry context)
# ---------------------------------------------------------------------------

_PHONE_UNANSWERED = [
    "No contesta. Segundo intento previsto para manana.",
    "Buzon de voz. Dejado mensaje con datos de contacto.",
    "No hi havia resposta. Es tornara a intentar la setmana que ve.",
    "No disponible. Se intentara nuevamente por la tarde.",
    "Truca i no contesta. Possible baixa d'activitat a la clinica.",
]

_PHONE_POSITIVE = [
    "Confirmado interes en retomar pedidos de material de composite. Enviamos catalogo actualizado.",
    "Contacte positiu. Interessat en les novetats de la gama de restauracio.",
    "Confirmo pedido grande previsto para el proximo mes. Muy receptivo.",
    "Molt bona disposicio. Fara la comanda a finals de setmana.",
    "Han cambiado al responsable de compras. El nuevo contacto es favorable al acuerdo.",
    "Excel.lent conversacio. Confirmada visita amb demostracio del producte.",
    "Gran receptivitat. Acord per a una comanda trimestral de material de endodoncia.",
]

_PHONE_NEUTRAL = [
    "Reconoce la bajada de pedidos. Comenta problemas de liquidez temporal. Sigue siendo cliente activo.",
    "Receptiu pero no pren decisions fins la propera reunio de la clinica.",
    "Mucho trabajo en la clinica, pide que le contactemos en 2 semanas.",
    "Situacio economica complicada. No descarta reprendre les comandes.",
    "Interes moderado. Necesita comparar precios con otro proveedor antes de decidir.",
]

_PHONE_NEGATIVE = [
    "No esta interesado. Trabajan ya con otro proveedor y estan satisfechos.",
    "La clinica ha reduit les activitats. Poc potencial a curt termini.",
    "Han encontrado un proveedor con mejores precios. Precio es el factor clave.",
    "No vol canviar de proveidor. Relacio consolidada amb la competencia.",
    "Clinica en proceso de cierre. No hay perspectiva de pedido.",
]

_VISIT_SUCCESSFUL_POSITIVE = [
    "Visita exitosa. Presentacion de nuevos materiales de ortodoncia con muy buena acogida. Pedido en 10 dias.",
    "Visita molt positiva. Hem tancat un compromis de comanda per al mes vinent.",
    "Revisada toda la cartera de materiales. Pedido confirmado para fin de mes.",
    "El dentista ha mostrado especial interes en los materiales de endodoncia. Demostracion programada.",
    "Visita productiva. Acuerdo marco para aprovisionamiento trimestral.",
    "El responsable de compres ha confirmat la comanda per email despres de la visita.",
]

_VISIT_SUCCESSFUL_NEUTRAL = [
    "Visita realizada. Interes moderado. Estan evaluando proveedores.",
    "Visita completada. Comentan reduccion de actividad pero no descartan reanudar.",
    "Han rebut la visita. Estan en proces de negociacio amb la central de la clinica.",
    "Visita neutra. Piden mas tiempo antes de tomar una decision.",
    "Recepcion cordial pero sin compromiso. Se programara seguimiento en un mes.",
]

_VISIT_UNSUCCESSFUL = [
    "La clinica estaba cerrada. Se intenta nueva visita la proxima semana.",
    "No estava el responsable de compres. Es deixa cataleg i es concorda nova visita.",
    "Visita fallida por reunion interna. Reprogramada para la proxima semana.",
    "El dentista estaba en intervencion. Se dejo tarjeta y muestra de producto.",
    "Clinica tancada per vacances. Es tornara a contactar al setembre.",
]

_EMAIL_RESPONDED_POSITIVE = [
    "Respuesta positiva. Solicitan propuesta comercial con precio de volumen.",
    "Han contestat per email. Interessats i demanen preus actualitzats.",
    "Replied positively. Request for updated catalog for restoration materials.",
    "Resposta favorable. Volen rebre visita del delegat la setmana que ve.",
    "Respuesta rapida. Confirman que retoman el nivel de pedidos anterior.",
]

_EMAIL_RESPONDED_NEUTRAL = [
    "Respuesta recibida. Piden mas tiempo para decidir.",
    "Resposta rebuda. Ho consultaran amb la direccio de la clinica.",
    "Replied asking for more information on pricing and delivery times.",
    "Contesten pero sense compromis clar. Seguiment previst.",
    "Han respondido. Evaluan la propuesta y responderan en 2 semanas.",
]

_EMAIL_NOT_RESPONDED = [
    "Email enviado con propuesta. Sin respuesta tras 3 dias habiles.",
    "Enviado email de seguimiento. Sense resposta de moment.",
    "Seguimiento por email enviado. Pendiente de respuesta.",
    "Segon email enviat. Sense confirmacio de recepcio.",
    "Email con catalogo adjunto. Sin acuse de recibo.",
]

_DISMISS_REASONS = [
    "La clinica ha fet un concurs de creditors. No facturable a curt termini.",
    "Client ha tancat la clinica temporalment per reforma. Revisio prevista en 6 mesos.",
    "Conflicte de preus no resoluble. El client prefereix un proveidor local.",
    "Han centralizado las compras en una sede diferente. No corresponde a este delegado.",
    "El dentista principal s'ha jubilat i la clinica ha tancat definitivament.",
    "Client irrecuperable - canvi de provelidor definitiu confirmat per escrit.",
    "Clinica cerrada por vacaciones hasta el 1 de septiembre.",
    "Comprador ha canviat. Nou contacte pendent d'identificar per la nova direccio.",
    "Baixa d'activitat per reforma de local. No hi ha previsio de compra en 4 mesos.",
    "Han firmado exclusividad con otro distribuidor. Sin margen de negociacion.",
]

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _uid() -> str:
    return str(uuid.uuid4())


def _parse_dt(s: str) -> datetime:
    """Parse ISO datetime string from SQLite (with or without tzinfo)."""
    s = s.strip()
    for fmt in (
        "%Y-%m-%d %H:%M:%S.%f+00:00",
        "%Y-%m-%d %H:%M:%S+00:00",
        "%Y-%m-%dT%H:%M:%S+00:00",
        "%Y-%m-%dT%H:%M:%S.%f+00:00",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            pass
    # Last resort
    return datetime.fromisoformat(s.replace("+00:00", "")).replace(tzinfo=timezone.utc)


def _ts_after(base: datetime, hours: float) -> str:
    """ISO string for (base + hours). Always after base -> positive delta."""
    return (base + timedelta(hours=hours)).isoformat()


def _pick(rng: random.Random, lst: list) -> str:
    return rng.choice(lst)


def _phone_interaction(rng: random.Random, ts: str, allow_positive: bool = True) -> dict:
    answered = rng.random() > 0.4
    rec: dict = {
        "id": _uid(),
        "handledBy": "phone",
        "answered": answered,
        "keepOpen": True,
        "submittedAt": ts,
    }
    if answered:
        result = rng.choices(
            ["positive", "neutral", "negative"],
            weights=[45, 35, 20] if allow_positive else [0, 50, 50],
        )[0]
        rec["result"] = result
        rec["notes"] = _pick(rng, {
            "positive": _PHONE_POSITIVE,
            "neutral":  _PHONE_NEUTRAL,
            "negative": _PHONE_NEGATIVE,
        }[result])
    else:
        rec["notes"] = _pick(rng, _PHONE_UNANSWERED)
    return rec


def _visit_interaction(rng: random.Random, ts: str, allow_positive: bool = True) -> dict:
    successful = rng.random() > 0.35
    rec: dict = {
        "id": _uid(),
        "handledBy": "visit",
        "visitSuccessful": successful,
        "keepOpen": True,
        "submittedAt": ts,
    }
    if successful:
        result = rng.choices(
            ["positive", "neutral"],
            weights=[65, 35] if allow_positive else [0, 100],
        )[0]
        rec["result"] = result
        rec["notes"] = _pick(rng, _VISIT_SUCCESSFUL_POSITIVE if result == "positive"
                             else _VISIT_SUCCESSFUL_NEUTRAL)
    else:
        rec["notes"] = _pick(rng, _VISIT_UNSUCCESSFUL)
    return rec


def _email_interaction(rng: random.Random, ts: str, allow_positive: bool = True) -> dict:
    responded = rng.random() > 0.55
    rec: dict = {
        "id": _uid(),
        "handledBy": "email",
        "emailResponseReceived": responded,
        "keepOpen": True,
        "submittedAt": ts,
    }
    if responded:
        result = rng.choices(
            ["positive", "neutral"],
            weights=[55, 45] if allow_positive else [0, 100],
        )[0]
        rec["result"] = result
        rec["notes"] = _pick(rng, _EMAIL_RESPONDED_POSITIVE if result == "positive"
                             else _EMAIL_RESPONDED_NEUTRAL)
    else:
        rec["notes"] = _pick(rng, _EMAIL_NOT_RESPONDED)
    return rec


def _random_interaction(rng: random.Random, ts: str, allow_positive: bool = True) -> dict:
    channel = rng.choices(["phone", "visit", "email"], weights=[50, 30, 20])[0]
    if channel == "phone":
        return _phone_interaction(rng, ts, allow_positive)
    if channel == "visit":
        return _visit_interaction(rng, ts, allow_positive)
    return _email_interaction(rng, ts, allow_positive)


def _build_attended_history(
    rng: random.Random, created_at: datetime, now: datetime
) -> tuple[list, list, str]:
    """
    Returns (interactions, events, attended_at_iso).
    All timestamps strictly AFTER created_at and BEFORE now.
    """
    # Cap max hours so attended_at is always in the past
    hours_available = (now - created_at).total_seconds() / 3600 - 0.5
    max_hrs = min(RESPONSE_TIME_MAX_HOURS, max(RESPONSE_TIME_MIN_HOURS + 0.1, hours_available))
    total_hours = rng.uniform(RESPONSE_TIME_MIN_HOURS, max_hrs)
    n = rng.randint(1, MAX_INTERACTIONS_ATTENDED)

    checkpoints = sorted(rng.uniform(0, total_hours * 0.85) for _ in range(n))
    interactions = []
    for i, hours in enumerate(checkpoints):
        is_last = i == len(checkpoints) - 1
        ts = _ts_after(created_at, hours)
        rec = _random_interaction(rng, ts, allow_positive=True)
        if is_last:
            rec["result"] = "positive"
            rec["keepOpen"] = False
            ch = rec["handledBy"]
            if ch == "phone":
                rec["answered"] = True
                rec["notes"] = _pick(rng, _PHONE_POSITIVE)
            elif ch == "visit":
                rec["visitSuccessful"] = True
                rec["notes"] = _pick(rng, _VISIT_SUCCESSFUL_POSITIVE)
            else:
                rec["emailResponseReceived"] = True
                rec["notes"] = _pick(rng, _EMAIL_RESPONDED_POSITIVE)
        interactions.append(rec)

    attended_at = _ts_after(created_at, total_hours)
    closed_event = {"id": _uid(), "type": "closed", "timestamp": attended_at}
    return interactions, [closed_event], attended_at


def _build_dismissed_history(
    rng: random.Random, created_at: datetime, now: datetime
) -> tuple[list, list, str, str]:
    """Returns (interactions, events, dismissed_at_iso, dismiss_reason)."""
    hours_available = (now - created_at).total_seconds() / 3600 - 0.5
    max_hrs = min(96.0, max(6.1, hours_available))
    total_hours = rng.uniform(6.0, max_hrs)
    n = rng.randint(1, MAX_INTERACTIONS_DISMISSED)
    checkpoints = sorted(rng.uniform(0, total_hours * 0.80) for _ in range(n))

    interactions = []
    for hours in checkpoints:
        ts = _ts_after(created_at, hours)
        rec = _random_interaction(rng, ts, allow_positive=False)
        interactions.append(rec)

    dismissed_at = _ts_after(created_at, total_hours)
    reason = _pick(rng, _DISMISS_REASONS)
    dismissed_event = {
        "id": _uid(), "type": "dismissed",
        "reason": reason, "timestamp": dismissed_at,
    }
    return interactions, [dismissed_event], dismissed_at, reason


def _build_touched_pending_history(
    rng: random.Random, created_at: datetime, now: datetime
) -> tuple[list, list]:
    """1-2 failed contacts; alert stays pending."""
    hours_available = (now - created_at).total_seconds() / 3600 - 0.5
    max_attempt_hrs = min(10.0, max(1.0, hours_available))
    n = rng.randint(1, MAX_INTERACTIONS_TOUCHED)
    hours_list = sorted(rng.uniform(0.5, max_attempt_hrs) for _ in range(n))

    interactions = []
    for hours in hours_list:
        ts = _ts_after(created_at, hours)
        channel = rng.choices(["phone", "visit", "email"], weights=[55, 25, 20])[0]
        if channel == "phone":
            rec = {
                "id": _uid(), "handledBy": "phone", "answered": False,
                "keepOpen": True, "notes": _pick(rng, _PHONE_UNANSWERED),
                "submittedAt": ts,
            }
        elif channel == "visit":
            rec = {
                "id": _uid(), "handledBy": "visit", "visitSuccessful": False,
                "keepOpen": True, "notes": _pick(rng, _VISIT_UNSUCCESSFUL),
                "submittedAt": ts,
            }
        else:
            rec = {
                "id": _uid(), "handledBy": "email", "emailResponseReceived": False,
                "keepOpen": True, "notes": _pick(rng, _EMAIL_NOT_RESPONDED),
                "submittedAt": ts,
            }
        interactions.append(rec)
    return interactions, []


def _build_east_attended(rng: random.Random, created_at: datetime, now: datetime) -> tuple[list, list, str]:
    """Positive attended history for east-zone boost (always positive result)."""
    hours_available = (now - created_at).total_seconds() / 3600 - 0.5
    max_hrs = min(72.0, max(4.1, hours_available))
    total_hours = rng.uniform(4.0, max_hrs)
    n = rng.randint(1, 3)

    EAST_PHONE = _PHONE_POSITIVE
    EAST_VISIT = _VISIT_SUCCESSFUL_POSITIVE
    EAST_EMAIL = _EMAIL_RESPONDED_POSITIVE

    checkpoints = sorted(rng.uniform(0, total_hours * 0.80) for _ in range(n))
    interactions = []
    for k, h in enumerate(checkpoints):
        is_last = k == len(checkpoints) - 1
        ts = _ts_after(created_at, h)
        channel = rng.choices(["phone", "visit", "email"], weights=[50, 30, 20])[0]
        if channel == "phone":
            rec = {"id": _uid(), "handledBy": "phone", "answered": True,
                   "result": "positive", "keepOpen": not is_last,
                   "notes": rng.choice(EAST_PHONE), "submittedAt": ts}
        elif channel == "visit":
            rec = {"id": _uid(), "handledBy": "visit", "visitSuccessful": True,
                   "result": "positive", "keepOpen": not is_last,
                   "notes": rng.choice(EAST_VISIT), "submittedAt": ts}
        else:
            rec = {"id": _uid(), "handledBy": "email", "emailResponseReceived": True,
                   "result": "positive", "keepOpen": not is_last,
                   "notes": rng.choice(EAST_EMAIL), "submittedAt": ts}
        interactions.append(rec)

    attended_at = _ts_after(created_at, total_hours)
    events = [{"id": _uid(), "type": "closed", "timestamp": attended_at}]
    return interactions, events, attended_at


# ---------------------------------------------------------------------------
# DB HELPERS
# ---------------------------------------------------------------------------

def _resolve_db_path(argv: list[str]) -> str:
    if len(argv) > 1:
        return argv[1]
    raw = os.environ.get("DATABASE_URL", "")
    if raw.startswith("sqlite:///"):
        candidate = raw[len("sqlite:///"):]
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
        return cur.fetchone()[0] > 10
    except sqlite3.OperationalError:
        return True  # column not present yet


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    db_path = _resolve_db_path(sys.argv)
    print(f"[seed_demo] DB: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    if _already_seeded(conn):
        print("[seed_demo] Already seeded - skipping.")
        conn.close()
        return

    now = datetime.now(timezone.utc)

    # Load all alerts with their created_at (set by migration 0010 to Mon-Wed)
    rows = conn.execute(
        "SELECT id, created_at FROM regional_alerts ORDER BY id"
    ).fetchall()
    total = len(rows)
    print(f"[seed_demo] Found {total} alerts. Seeding with created_at-relative timestamps...")

    rng = random.Random(SEED)
    indices = list(range(total))
    rng.shuffle(indices)  # deterministic shuffle

    n_attended  = int(total * FRAC_ATTENDED)
    n_dismissed = int(total * FRAC_DISMISSED)
    n_touched   = int(total * FRAC_TOUCHED_PENDING)

    attended_idx  = set(indices[:n_attended])
    dismissed_idx = set(indices[n_attended: n_attended + n_dismissed])
    touched_idx   = set(indices[n_attended + n_dismissed: n_attended + n_dismissed + n_touched])

    updates: list[tuple] = []

    for i, row in enumerate(rows):
        aid = row["id"]
        created_at = _parse_dt(row["created_at"])

        if i in attended_idx:
            interactions, events, attended_at = _build_attended_history(rng, created_at, now)
            updates.append((
                json.dumps(interactions, ensure_ascii=False),
                json.dumps(events, ensure_ascii=False),
                "attended", attended_at, None, None, aid,
            ))
        elif i in dismissed_idx:
            interactions, events, dismissed_at, reason = _build_dismissed_history(rng, created_at, now)
            updates.append((
                json.dumps(interactions, ensure_ascii=False),
                json.dumps(events, ensure_ascii=False),
                "dismissed", None, dismissed_at, reason, aid,
            ))
        elif i in touched_idx:
            interactions, events = _build_touched_pending_history(rng, created_at, now)
            updates.append((
                json.dumps(interactions, ensure_ascii=False),
                json.dumps(events, ensure_ascii=False),
                "pending", None, None, None, aid,
            ))
        # else: pure pending - no update

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

    n_pure = total - n_attended - n_dismissed - n_touched
    print(
        f"[seed_demo] Global seed done. "
        f"Attended={n_attended}  Dismissed={n_dismissed}  "
        f"Touched-pending={n_touched}  Pure-pending={n_pure}"
    )

    # -----------------------------------------------------------------------
    # East-zone boost: convert most remaining pending east alerts to attended
    # so the east region shows a healthy score instead of red/critical.
    # -----------------------------------------------------------------------
    east_pending = conn.execute(
        """
        SELECT ra.id, ra.created_at
        FROM regional_alerts ra
        JOIN clients c ON ra.client_id = c.id
        WHERE c.zone = 'east' AND ra.status = 'pending'
        ORDER BY ra.id
        """
    ).fetchall()

    if len(east_pending) > EAST_PENDING_KEEP:
        east_rng = random.Random(99)  # separate seed for boost pass
        to_attend = east_pending[EAST_PENDING_KEEP:]  # keep first N as pending
        east_updates = []
        for row in to_attend:
            created_at = _parse_dt(row["created_at"])
            interactions, events, attended_at = _build_east_attended(east_rng, created_at, now)
            east_updates.append((
                json.dumps(interactions, ensure_ascii=False),
                json.dumps(events, ensure_ascii=False),
                "attended", attended_at, row["id"],
            ))
        conn.executemany(
            """
            UPDATE regional_alerts
            SET interactions_json = ?,
                events_json       = ?,
                status            = 'attended',
                attended_at       = ?
            WHERE id = ?
            """,
            [(u[0], u[1], u[3], u[4]) for u in east_updates],
        )
        conn.commit()
        print(f"[seed_demo] East boost: {len(east_updates)} alerts -> attended "
              f"(keeping {EAST_PENDING_KEEP} pending).")
    else:
        print(f"[seed_demo] East boost: only {len(east_pending)} pending east alerts, no boost needed.")

    conn.close()
    print("[seed_demo] Done.")


if __name__ == "__main__":
    main()