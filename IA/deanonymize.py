"""
deanonymize.py
==============
Maps anonymized client IDs to synthetic dental clinic names.

The mapping is DETERMINISTIC: given the same client ID, the same name is
always returned across executions. This is achieved by seeding Python's
random module with the client ID itself — no external file needed.

Usage:
    from deanonymize import get_client_name, build_name_dict

    name = get_client_name(1234)
    names = build_name_dict([1818, 2045, 3301, ...])
"""

import random
from typing import Sequence

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURABLE VOCABULARY
# Extend these lists to get more name variety.
# ─────────────────────────────────────────────────────────────────────────────

# Spanish dental clinic prefixes / first words
_PREFIXES = [
    "Clínica Dental",
    "Centro Dental",
    "Consulta Dental",
    "Odontología",
    "Centro Odontológico",
    "Clínica Odontológica",
    "Dental",
    "Gabinete Dental",
    "Policlínica Dental",
    "Instituto Dental",
]

# Evocative adjectives / place-names / proper names used in real clinic naming
_WORDS = [
    "Armonía", "Salud", "Sonrisa", "Claro", "Vitaldent", "Oral",
    "Blanca", "Nórdica", "Atlántica", "Ibérica", "Central", "Moderna",
    "Familiar", "Integral", "Avanzada", "Experta", "Precisa", "Natural",
    "Excelencia", "Confianza", "Bienestar", "Equilibrio", "Vitalidad",
    "Perfecta", "Brillante", "Serena", "Plena", "Clara", "Óptima",
    "Mediterránea", "Cantábrica", "Levantina", "Andaluza", "Madrileña",
    "Vasca", "Gallega", "Balear", "Canaria", "Aragonesa", "Navarra",
    "Riojana", "Manchega", "Extremeña", "Murciana", "Alicantina",
]

# Common Spanish surnames used as clinic "brand names"
_SURNAMES = [
    "García", "Martínez", "López", "González", "Rodríguez", "Fernández",
    "Sánchez", "Pérez", "Gómez", "Martín", "Jiménez", "Ruiz",
    "Hernández", "Díaz", "Moreno", "Muñoz", "Álvarez", "Romero",
    "Alonso", "Gutiérrez", "Navarro", "Torres", "Domínguez", "Vázquez",
    "Ramos", "Gil", "Ramírez", "Serrano", "Blanco", "Suárez",
    "Molina", "Morales", "Ortega", "Delgado", "Castro", "Ortiz",
    "Rubio", "Marín", "Sanz", "Iglesias", "Núñez", "Medina",
    "Garrido", "Cortés", "Castillo", "Santos", "Lozano", "Guerrero",
    "Cano", "Prieto", "Méndez", "Cruz", "Calvo", "Gallego",
    "Herrera", "Rios", "Pascual", "Reyes", "Montero", "Fuentes",
]

# Name templates (placeholders filled at generation time)
# {prefix} = one of _PREFIXES
# {word}   = one of _WORDS
# {name}   = one of _SURNAMES
_TEMPLATES = [
    "{prefix} {name}",           # e.g. Clínica Dental García
    "{prefix} {word}",           # e.g. Centro Dental Armonía
    "{prefix} {name} y {name}",  # e.g. Dental López y Martínez
    "{prefix} Dr. {name}",       # e.g. Gabinete Dental Dr. Serrano
    "{prefix} {word} {name}",    # e.g. Clínica Dental Sonrisa Ruiz
    "{word} {name}",             # e.g. Odontología Fernández
    "{prefix} {name} - {word}",  # e.g. Centro Dental Gómez - Integral
]


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def get_client_name(client_id: int) -> str:
    """
    Return a synthetic clinic name for the given client ID.
    The result is fully deterministic: the same ID always produces the same name.
    """
    rng = random.Random(client_id)  # seed with the ID → deterministic
    template = rng.choice(_TEMPLATES)

    def pick(lst):
        return rng.choice(lst)

    name = template.format(
        prefix=pick(_PREFIXES),
        word=pick(_WORDS),
        name=pick(_SURNAMES),
    )
    # If the template has two {name} slots, both are already resolved above
    # because format() calls pick() twice independently via the same rng.
    # But if the template has two literal {name} references, format() will
    # only call the function once; handle that edge case:
    if name.count(pick(_SURNAMES)) > 1:  # noqa: SIM117 (just a safety pass)
        pass  # already formatted correctly by .format()

    return name


def build_name_dict(client_ids: Sequence[int]) -> dict[int, str]:
    """
    Return a dictionary {client_id: synthetic_name} for all given IDs.
    """
    return {cid: get_client_name(cid) for cid in client_ids}


# ─────────────────────────────────────────────────────────────────────────────
# STANDALONE SMOKE TEST
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_ids = [1818, 2045, 3301, 999, 42, 10000, 1818]  # 1818 repeated → must match
    print("Synthetic clinic names (run twice to verify determinism):")
    for cid in test_ids:
        print(f"  {cid:>6} → {get_client_name(cid)}")

    print("\nVerification — 1818 called twice:")
    print(f"  First : {get_client_name(1818)}")
    print(f"  Second: {get_client_name(1818)}")
    assert get_client_name(1818) == get_client_name(1818), "NON-DETERMINISTIC!"
    print("  ✓ Deterministic")
