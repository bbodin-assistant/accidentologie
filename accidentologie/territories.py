"""Définition réutilisable d'un territoire d'analyse."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class Territory:
    """Nom d'affichage et codes INSEE communaux d'un territoire."""

    name: str
    communes: tuple[str, ...]

    def __init__(self, name: str, communes: Iterable[str | int]):
        normalized = tuple(dict.fromkeys(str(code).strip().upper() for code in communes))
        if not name.strip():
            raise ValueError("Le nom du territoire ne peut pas être vide")
        if not normalized:
            raise ValueError("Un territoire doit contenir au moins une commune")
        object.__setattr__(self, "name", name.strip())
        object.__setattr__(self, "communes", normalized)


CARA = Territory(
    "Communauté d'agglomération Royan Atlantique (CARA)",
    (
        "17015", "17021", "17034", "17060", "17064", "17068", "17079",
        "17098", "17119", "17131", "17152", "17155", "17160", "17183",
        "17151", "17452", "17097", "17225", "17228", "17230", "17247",
        "17248", "17306", "17307", "17311", "17333", "17380", "17393",
        "17409", "17421", "17425", "17437", "17461",
    ),
)

ROYAN = Territory("Royan", ("17306",))
