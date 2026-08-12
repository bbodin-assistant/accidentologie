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
