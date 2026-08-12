"""Téléchargement des tables annuelles BAAC depuis data.gouv.fr."""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


# Identifiant stable data.gouv.fr, indépendant du titre et de l'année maximale
# affichée dans le slug public du jeu de données.
DATASET_ID = "53698f4ca3a729239d2036df"
API_URL = f"https://www.data.gouv.fr/api/1/datasets/{DATASET_ID}/"
TABLES = ("caracteristiques", "lieux", "vehicules", "usagers")
ANALYSIS_TABLES = ("caracteristiques", "vehicules", "usagers")
YEAR_PATTERN = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")
ProgressCallback = Callable[[Path, int, int | None], None]


def _request(url: str, timeout: int = 30):
    return urlopen(
        Request(url, headers={"User-Agent": "accidentologie-python/0.1"}),
        timeout=timeout,
    )


def _fetch_dataset() -> dict[str, Any]:
    with _request(API_URL) as response:
        return json.load(response)


def _table_from_title(title: str) -> str | None:
    normalized = title.casefold()
    if "immatricul" in normalized:
        return None
    if normalized.startswith(("caract", "carcter")):
        return "caracteristiques"
    for table in TABLES[1:]:
        if normalized.startswith(table):
            return table
    return None


def _annual_resources(
    dataset: dict[str, Any],
) -> dict[tuple[int, str], dict[str, Any]]:
    selected: dict[tuple[int, str], dict[str, Any]] = {}
    for resource in dataset.get("resources", []):
        title = str(resource.get("title", ""))
        table = _table_from_title(title)
        year_match = YEAR_PATTERN.search(title)
        if (
            table is None
            or year_match is None
            or str(resource.get("format", "")).casefold() != "csv"
            or not resource.get("url")
        ):
            continue
        key = (int(year_match.group(1)), table)
        previous = selected.get(key)
        if previous is None or str(resource.get("last_modified", "")) > str(
            previous.get("last_modified", "")
        ):
            selected[key] = resource
    return selected


def _format_bytes(byte_count: int) -> str:
    value = float(byte_count)
    for unit in ("o", "Kio", "Mio", "Gio"):
        if value < 1024 or unit == "Gio":
            return f"{value:.1f} {unit}"
        value /= 1024
    raise AssertionError("unreachable")


def console_progress(path: Path, downloaded: int, total: int | None) -> None:
    """Affiche la progression d'un téléchargement dans un terminal."""
    if total:
        status = (
            f"{downloaded / total * 100:6.2f}%  "
            f"{_format_bytes(downloaded)} / {_format_bytes(total)}"
        )
    else:
        status = _format_bytes(downloaded)
    print(f"\rTéléchargement {path}  {status}", end="", flush=True)


def _download_file(
    url: str,
    destination: Path,
    *,
    force: bool,
    retries: int,
    progress: ProgressCallback | None,
) -> bool:
    if destination.exists() and not force:
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    for attempt in range(1, retries + 1):
        try:
            downloaded = 0
            with _request(url) as response, temporary.open("wb") as output:
                length = response.headers.get("Content-Length")
                total = int(length) if length else None
                while chunk := response.read(256 * 1024):
                    output.write(chunk)
                    downloaded += len(chunk)
                    if progress is not None:
                        progress(destination, downloaded, total)
            if progress is console_progress:
                print()
            if downloaded == 0:
                raise OSError("le serveur a renvoyé un fichier vide")
            if total is not None and downloaded != total:
                raise OSError(f"téléchargement incomplet : {downloaded}/{total} octets")
            temporary.replace(destination)
            return True
        except KeyboardInterrupt:
            temporary.unlink(missing_ok=True)
            raise
        except (HTTPError, URLError, OSError):
            temporary.unlink(missing_ok=True)
            if attempt == retries:
                raise
            time.sleep(2 ** (attempt - 1))
    return False


def download_csv_files(
    years: Iterable[int] | int | None = None,
    *,
    data_dir: str | Path = "data",
    tables: Iterable[str] | str = TABLES,
    force: bool = False,
    retries: int = 3,
    progress: ProgressCallback | None = console_progress,
) -> list[Path]:
    """Télécharge les CSV BAAC demandés pour les années sélectionnées.

    Retourne uniquement les chemins effectivement téléchargés. Les fichiers déjà
    présents sont conservés, sauf avec ``force=True``. Par défaut, les quatre
    tables officielles sont récupérées ; ``tables=ANALYSIS_TABLES`` limite le
    téléchargement aux trois tables utilisées par les analyses du package.
    """
    if retries < 1:
        raise ValueError("`retries` doit valoir au moins 1")
    requested_tables = [tables] if isinstance(tables, str) else list(tables)
    requested_tables = list(
        dict.fromkeys(str(table).strip().casefold() for table in requested_tables)
    )
    invalid_tables = sorted(set(requested_tables).difference(TABLES))
    if invalid_tables or not requested_tables:
        raise ValueError(
            "Tables BAAC invalides : "
            + (", ".join(invalid_tables) if invalid_tables else "liste vide")
            + f". Valeurs acceptées : {', '.join(TABLES)}."
        )
    dataset = _fetch_dataset()
    resources = _annual_resources(dataset)
    if not resources:
        raise RuntimeError("aucune ressource annuelle CSV trouvée sur data.gouv.fr")
    available = sorted({year for year, _ in resources})
    if years is None:
        selected = available
    elif isinstance(years, (int, str)):
        selected = [int(years)]
    else:
        selected = sorted({int(year) for year in years})
    if not selected:
        raise ValueError("La liste `years` ne peut pas être vide")
    missing_years = sorted(set(selected).difference(available))
    if missing_years:
        raise ValueError(f"Années absentes de la source : {missing_years}")
    missing_tables = [
        (year, table)
        for year in selected
        for table in requested_tables
        if (year, table) not in resources
    ]
    if missing_tables:
        raise RuntimeError(f"Tables absentes de la source : {missing_tables}")

    directory = Path(data_dir).expanduser()
    downloaded: list[Path] = []
    for year in selected:
        for table in requested_tables:
            destination = directory / str(year) / f"{table}-{year}.csv"
            if _download_file(
                str(resources[(year, table)]["url"]),
                destination,
                force=force,
                retries=retries,
                progress=progress,
            ):
                downloaded.append(destination)
    return downloaded
