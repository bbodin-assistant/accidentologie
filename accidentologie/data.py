"""Chargement et normalisation des fichiers annuels BAAC."""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

import pandas as pd


SEVERITY_RANK = {"-1": -1, "1": 0, "4": 1, "3": 2, "2": 3}
RANK_TO_SEVERITY_CODE = {rank: code for code, rank in SEVERITY_RANK.items()}
SEVERITY_LABELS = {
    "-1": "Inconnue",
    "1": "Indemne seulement",
    "4": "Léger",
    "3": "Blessé hospitalisé",
    "2": "Mortel",
}

# La collecte des blessés hospitalisés connaît une rupture méthodologique à
# partir des données 2018. Cette constante est publique afin que les rendus puissent
# signaler explicitement la rupture au lieu de présenter une série homogène.
HOSPITALIZED_SERIES_BREAK_YEAR = 2018

VEHICLE_LABELS = {
    "0": "Véhicule indéterminé",
    "1": "Bicyclette",
    "2": "Cyclomoteur < 50 cm³",
    "3": "Voiturette / quadricycle carrossé",
    "4": "Scooter immatriculé (ancienne catégorie)",
    "5": "Motocyclette (ancienne catégorie)",
    "6": "Side-car (ancienne catégorie)",
    "7": "Voiture particulière",
    "8": "Voiture + caravane (ancienne catégorie)",
    "9": "Voiture + remorque (ancienne catégorie)",
    "10": "Véhicule utilitaire 1,5–3,5 t",
    "11": "Utilitaire + caravane (ancienne catégorie)",
    "12": "Utilitaire + remorque (ancienne catégorie)",
    "13": "Poids lourd 3,5–7,5 t",
    "14": "Poids lourd > 7,5 t",
    "15": "Poids lourd + remorque",
    "16": "Tracteur routier",
    "17": "Tracteur routier + semi-remorque",
    "18": "Transport en commun (ancienne catégorie)",
    "19": "Tramway (ancienne catégorie)",
    "20": "Engin spécial",
    "21": "Tracteur agricole",
    "30": "Scooter < 50 cm³",
    "31": "Motocyclette 50–125 cm³",
    "32": "Scooter 50–125 cm³",
    "33": "Motocyclette > 125 cm³",
    "34": "Scooter > 125 cm³",
    "35": "Quad léger <= 50 cm³",
    "36": "Quad lourd > 50 cm³",
    "37": "Autobus",
    "38": "Autocar",
    "39": "Train",
    "40": "Tramway",
    "41": "Trois-roues <= 50 cm³",
    "42": "Trois-roues 50–125 cm³",
    "43": "Trois-roues > 125 cm³",
    "50": "Engin de déplacement personnel motorisé",
    "60": "Engin de déplacement personnel sans moteur",
    "80": "Vélo à assistance électrique",
    "99": "Autre véhicule",
    "-1": "Véhicule inconnu",
}

OUTPUT_COLUMNS = [
    "accident_id",
    "year",
    "date",
    "time",
    "department_code",
    "commune_code",
    "address",
    "latitude",
    "longitude",
    "has_coordinates",
    "severity_code",
    "severity",
    "number_killed",
    "number_hospitalized",
    "number_slightly_injured",
    "number_uninjured",
    "number_users",
    "number_vehicles",
    "vehicle_codes",
    "vehicle_types",
]


def _delimiter(path: Path) -> str:
    with path.open("rb") as csv_file:
        header = csv_file.readline()
    candidates = (b",", b";", b"\t")
    detected = max(candidates, key=header.count)
    if header.count(detected) == 0:
        raise ValueError(f"Séparateur CSV indétectable dans {path}")
    return detected.decode("ascii")


def _read_baac(
    path: Path,
    year: int,
    columns: set[str],
    *,
    required_columns: set[str] | None = None,
) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Fichier BAAC absent : {path}. Utilisez "
            "`accidentologie.download_csv_files(...)` ou `python main.py --download`."
        )
    encoding = "latin-1" if year <= 2018 else "utf-8"
    dataframe = pd.read_csv(
        path,
        sep=_delimiter(path),
        encoding=encoding,
        dtype=str,
        usecols=lambda column: column in columns,
        low_memory=False,
    )
    required = columns if required_columns is None else required_columns
    missing = sorted(required.difference(dataframe.columns))
    if missing:
        raise ValueError(
            f"Schéma BAAC incompatible dans {path} : colonnes obligatoires absentes : "
            + ", ".join(missing)
        )
    return dataframe


def _clean_code(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype("Int64").astype("string")


def _available_years(data_dir: Path) -> list[int]:
    years = []
    if data_dir.exists():
        for child in data_dir.iterdir():
            if child.is_dir() and re.fullmatch(r"(?:19|20)\d{2}", child.name):
                year = int(child.name)
                if (child / f"caracteristiques-{year}.csv").exists():
                    years.append(year)
    return sorted(years)


def _normalize_years(years: Iterable[int] | int | None, data_dir: Path) -> list[int]:
    available = _available_years(data_dir)
    if not available:
        raise FileNotFoundError(
            f"Aucune donnée annuelle trouvée dans {data_dir.resolve()}. "
            "Utilisez `accidentologie.download_csv_files(...)` ou "
            "`python main.py --download`."
        )
    if years is None:
        return available
    if isinstance(years, (int, str)):
        requested = [int(years)]
    else:
        requested = sorted({int(year) for year in years})
    if not requested:
        raise ValueError("La liste `years` ne peut pas être vide")
    missing = sorted(set(requested).difference(available))
    if missing:
        raise ValueError(
            f"Années indisponibles : {missing}. Années présentes : {available[0]}–{available[-1]}."
        )
    return requested


def _normalize_communes(
    communes: Iterable[str | int] | str | int | None,
) -> set[str] | None:
    if communes is None:
        return None
    values = [communes] if isinstance(communes, (str, int)) else list(communes)
    normalized = {str(value).strip().upper() for value in values}
    invalid = sorted(code for code in normalized if not re.fullmatch(r"(?:\d{5}|2[AB]\d{3})", code))
    if invalid:
        raise ValueError(
            "Codes commune invalides : "
            + ", ".join(invalid)
            + ". Utilisez les codes INSEE à cinq caractères, par exemple '17306'."
        )
    return normalized


def _commune_codes(characteristics: pd.DataFrame, year: int) -> pd.Series:
    commune = characteristics["com"].astype("string").str.strip().str.upper()
    if year >= 2019:
        return commune
    department = characteristics["dep"].astype("string").str.strip().str.upper()
    # Dans l'ancien schéma, le département est codé sur trois caractères
    # (170, 2A0, 972...) et `com` sur trois. Les deux premiers caractères du
    # département suivis de `com` redonnent le code INSEE communal à 5 signes.
    return department.str[:2] + commune.str.zfill(3)


def _department_codes(characteristics: pd.DataFrame, year: int) -> pd.Series:
    department = characteristics["dep"].astype("string").str.strip().str.upper()
    if year >= 2019:
        return department.str.zfill(2)
    mainland_or_corsica = department.str.endswith("0", na=False)
    return department.where(~mainland_or_corsica, department.str[:2])


def _coordinates(characteristics: pd.DataFrame, year: int) -> tuple[pd.Series, pd.Series]:
    latitude = pd.to_numeric(
        characteristics["lat"].astype("string").str.replace(",", ".", regex=False),
        errors="coerce",
    ).astype(float)
    longitude = pd.to_numeric(
        characteristics["long"].astype("string").str.replace(",", ".", regex=False),
        errors="coerce",
    ).astype(float)
    if year <= 2018:
        latitude = latitude.where(latitude.abs().lt(100), latitude / 100000)
        longitude = longitude.where(longitude.abs().lt(100), longitude / 100000)
    valid = latitude.between(-90, 90) & longitude.between(-180, 180)
    valid &= ~(latitude.eq(0) & longitude.eq(0))
    return latitude.where(valid), longitude.where(valid)


def _normalize_time(series: pd.Series) -> pd.Series:
    raw = series.astype("string").str.strip().str.replace("h", ":", regex=False)
    compact = raw.str.replace(":", "", regex=False).str.zfill(4)
    valid = compact.str.fullmatch(r"(?:[01]\d|2[0-3])[0-5]\d", na=False)
    result = pd.Series(pd.NA, index=series.index, dtype="string")
    result.loc[valid] = compact.loc[valid].str[:2] + ":" + compact.loc[valid].str[2:]
    return result


def _load_year(data_dir: Path, year: int, communes: set[str] | None) -> pd.DataFrame:
    year_dir = data_dir / str(year)
    characteristics = _read_baac(
        year_dir / f"caracteristiques-{year}.csv",
        year,
        {
            "Num_Acc",
            "Accident_Id",
            "jour",
            "mois",
            "an",
            "hrmn",
            "dep",
            "com",
            "adr",
            "lat",
            "long",
        },
        required_columns={
            "jour", "mois", "hrmn", "dep", "com", "adr", "lat", "long"
        },
    )
    if not {"Num_Acc", "Accident_Id"}.intersection(characteristics.columns):
        raise ValueError(
            f"Schéma BAAC incompatible dans {year_dir}: "
            "identifiant Num_Acc/Accident_Id absent"
        )
    characteristics = characteristics.rename(columns={"Accident_Id": "Num_Acc"})
    characteristics["Num_Acc"] = characteristics["Num_Acc"].astype("string").str.strip()
    characteristics["commune_code"] = _commune_codes(characteristics, year)
    characteristics["department_code"] = _department_codes(characteristics, year)
    if communes is not None:
        characteristics = characteristics[
            characteristics["commune_code"].isin(communes)
        ].copy()
    if characteristics.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    if characteristics["Num_Acc"].duplicated().any():
        raise ValueError(f"Identifiants d'accident dupliqués dans l'année {year}")

    accident_ids = set(characteristics["Num_Acc"])
    users = _read_baac(
        year_dir / f"usagers-{year}.csv",
        year,
        {"Num_Acc", "grav"},
        required_columns={"Num_Acc", "grav"},
    )
    users["Num_Acc"] = users["Num_Acc"].astype("string").str.strip()
    users = users[users["Num_Acc"].isin(accident_ids)].copy()
    users["severity_code_user"] = _clean_code(users["grav"]).fillna("-1")
    users["severity_rank"] = users["severity_code_user"].map(SEVERITY_RANK).fillna(-1)
    user_summary = users.groupby("Num_Acc", as_index=False).agg(
        severity_rank=("severity_rank", "max"),
        number_killed=("severity_code_user", lambda values: values.eq("2").sum()),
        number_hospitalized=("severity_code_user", lambda values: values.eq("3").sum()),
        number_slightly_injured=("severity_code_user", lambda values: values.eq("4").sum()),
        number_uninjured=("severity_code_user", lambda values: values.eq("1").sum()),
        number_users=("severity_code_user", "size"),
    )

    vehicles = _read_baac(
        year_dir / f"vehicules-{year}.csv",
        year,
        {"Num_Acc", "num_veh", "id_vehicule", "catv"},
        required_columns={"Num_Acc", "catv"},
    )
    vehicles["Num_Acc"] = vehicles["Num_Acc"].astype("string").str.strip()
    vehicles = vehicles[vehicles["Num_Acc"].isin(accident_ids)].copy()
    vehicles["vehicle_code"] = _clean_code(vehicles["catv"]).fillna("-1")
    vehicles["vehicle_type"] = vehicles["vehicle_code"].map(VEHICLE_LABELS).fillna(
        "Véhicule inconnu"
    )
    vehicle_summary = vehicles.groupby("Num_Acc", as_index=False).agg(
        number_vehicles=("vehicle_code", "size"),
        vehicle_codes=("vehicle_code", lambda values: ";".join(sorted(set(values)))),
        vehicle_types=("vehicle_type", lambda values: " ; ".join(sorted(set(values)))),
    )

    latitude, longitude = _coordinates(characteristics, year)
    characteristics["latitude"] = latitude
    characteristics["longitude"] = longitude
    characteristics["date"] = pd.to_datetime(
        {
            "year": year,
            "month": pd.to_numeric(characteristics["mois"], errors="coerce"),
            "day": pd.to_numeric(characteristics["jour"], errors="coerce"),
        },
        errors="coerce",
    )
    characteristics["time"] = _normalize_time(characteristics["hrmn"])
    characteristics["year"] = year
    characteristics = characteristics.rename(
        columns={"Num_Acc": "accident_id", "adr": "address"}
    )

    result = characteristics.merge(
        user_summary.rename(columns={"Num_Acc": "accident_id"}),
        on="accident_id",
        how="left",
        validate="one_to_one",
    ).merge(
        vehicle_summary.rename(columns={"Num_Acc": "accident_id"}),
        on="accident_id",
        how="left",
        validate="one_to_one",
    )
    result["severity_rank"] = result["severity_rank"].fillna(-1).astype(int)
    result["severity_code"] = result["severity_rank"].map(RANK_TO_SEVERITY_CODE)
    result["severity"] = result["severity_code"].map(SEVERITY_LABELS)
    count_columns = [
        "number_killed",
        "number_hospitalized",
        "number_slightly_injured",
        "number_uninjured",
        "number_users",
        "number_vehicles",
    ]
    result[count_columns] = result[count_columns].fillna(0).astype(int)
    result["has_coordinates"] = result["latitude"].notna() & result["longitude"].notna()
    return result[OUTPUT_COLUMNS]


def get_dataframe(
    years: Iterable[int] | int | None = None,
    communes: Iterable[str | int] | str | int | None = None,
    *,
    data_dir: str | Path = "data",
) -> pd.DataFrame:
    """Retourne un DataFrame normalisé contenant une ligne par accident.

    Args:
        years: Année, liste d'années, ou ``None`` pour toutes les années locales.
        communes: Code INSEE, liste de codes, ou ``None`` pour toute la France.
        data_dir: Répertoire contenant les sous-répertoires annuels BAAC.

    Les filtres sont appliqués pendant la lecture afin de limiter la mémoire utilisée.
    Les codes communaux des fichiers 2005–2018 sont convertis au format INSEE actuel
    à cinq caractères, sans reconstruire les changements de périmètre historiques.
    """
    directory = Path(data_dir).expanduser()
    selected_years = _normalize_years(years, directory)
    selected_communes = _normalize_communes(communes)
    frames = [
        _load_year(directory, year, selected_communes) for year in selected_years
    ]
    result = pd.concat(frames, ignore_index=True)
    if result.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    return result.sort_values(["year", "accident_id"]).reset_index(drop=True)
