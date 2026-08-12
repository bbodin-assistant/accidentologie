"""Définition réutilisable d'un territoire d'analyse."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
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
        invalid = [
            code
            for code in normalized
            if not re.fullmatch(r"(?:\d{5}|2[AB]\d{3})", code)
        ]
        if invalid:
            raise ValueError("Codes INSEE communaux invalides : " + ", ".join(invalid))
        object.__setattr__(self, "name", name.strip())
        object.__setattr__(self, "communes", normalized)

    @classmethod
    def from_geojson(
        cls,
        path: str | Path,
        *,
        name: str | None = None,
        code_property: str = "code",
    ) -> "Territory":
        """Construit un territoire depuis les propriétés de communes d'un GeoJSON."""
        source = Path(path)
        payload = json.loads(source.read_text(encoding="utf-8"))
        features = payload.get("features", [])
        codes = [
            feature.get("properties", {}).get(code_property)
            for feature in features
            if feature.get("properties", {}).get(code_property) is not None
        ]
        if not codes:
            raise ValueError(
                f"Aucun code communal trouvé dans {source} avec la propriété "
                f"{code_property!r}"
            )
        return cls(name or source.stem.replace("_", " ").replace("-", " "), codes)
