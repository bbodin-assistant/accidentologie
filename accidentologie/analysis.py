"""Agrégations génériques construites sur le DataFrame canonique."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from .data import (
    VEHICLE_LABELS,
    _clean_code,
    _normalize_communes,
    _normalize_years,
    _read_baac,
    get_dataframe,
)


USER_CATEGORY = {
    "1": "Conducteur",
    "2": "Passager",
    "3": "Piéton",
    # Ancien schéma BAAC : piéton en roller ou trottinette.
    "4": "Piéton",
}
SEX = {"1": "Homme", "2": "Femme"}
USER_SEVERITY = {
    "1": "Indemne",
    "2": "Tué",
    "3": "Blessé hospitalisé",
    "4": "Blessé léger",
    "-1": "Inconnue",
}


def get_accidents_per_year(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Compte les accidents distincts par année et gravité."""
    required = {"accident_id", "year", "severity_code", "severity"}
    missing = required.difference(dataframe.columns)
    if missing:
        raise ValueError(f"Colonnes absentes : {sorted(missing)}")
    return (
        dataframe.groupby(
            ["year", "severity_code", "severity"], as_index=False, dropna=False
        )
        .agg(accident_count=("accident_id", "nunique"))
        .sort_values(["year", "severity_code"])
        .reset_index(drop=True)
    )


def get_vehicle_severity_table(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Compte les accidents par type de véhicule impliqué et gravité.

    Un accident multivéhicule figure une fois pour chaque type distinct impliqué.
    """
    required = {"accident_id", "severity", "vehicle_types"}
    missing = required.difference(dataframe.columns)
    if missing:
        raise ValueError(f"Colonnes absentes : {sorted(missing)}")
    expanded = dataframe[list(required)].copy()
    expanded["vehicle_type"] = (
        expanded["vehicle_types"].fillna("Véhicule inconnu").str.split(" ; ")
    )
    expanded = expanded.explode("vehicle_type").drop_duplicates(
        ["accident_id", "vehicle_type"]
    )
    return (
        expanded.groupby(["vehicle_type", "severity"], as_index=False)
        .agg(accident_count=("accident_id", "nunique"))
        .sort_values(["vehicle_type", "severity"])
        .reset_index(drop=True)
    )


def _mobility_group(user_category: str, vehicle_code: str) -> str:
    if user_category == "Piéton":
        return "Piéton"
    if vehicle_code in {"1", "80"}:
        return "Vélo / VAE"
    if vehicle_code in {"50", "60"}:
        return "EDP"
    if vehicle_code in {"2", "30"}:
        return "Cyclomoteur / scooter <50"
    if vehicle_code in {"4", "5", "6", "31", "32", "33", "34", "41", "42", "43"}:
        return "Moto / scooter / 3RM"
    if vehicle_code in {"3", "7", "8", "9"}:
        return "Voiture / voiturette"
    if vehicle_code in {"10", "11", "12"}:
        return "Véhicule utilitaire"
    if vehicle_code in {"13", "14", "15", "16", "17", "18", "37", "38"}:
        return "Poids lourd / transport collectif"
    return "Autres véhicules"


def get_victim_dataframe(
    years: Iterable[int] | int | None = None,
    communes: Iterable[str | int] | str | int | None = None,
    *,
    data_dir: str | Path = "data",
    injured_only: bool = False,
) -> pd.DataFrame:
    """Retourne une ligne par usager des accidents du territoire demandé."""
    directory = Path(data_dir).expanduser()
    selected_years = _normalize_years(years, directory)
    selected_communes = _normalize_communes(communes)
    frames: list[pd.DataFrame] = []
    for year in selected_years:
        accidents = get_dataframe(
            years=year, communes=selected_communes, data_dir=directory
        )
        if accidents.empty:
            continue
        accident_ids = set(accidents["accident_id"])
        year_dir = directory / str(year)
        users = _read_baac(
            year_dir / f"usagers-{year}.csv",
            year,
            {
                "Num_Acc", "id_usager", "id_vehicule", "num_veh", "catu",
                "grav", "sexe", "an_nais",
            },
            required_columns={
                "Num_Acc", "num_veh", "catu", "grav", "sexe", "an_nais"
            },
        )
        vehicles = _read_baac(
            year_dir / f"vehicules-{year}.csv",
            year,
            {"Num_Acc", "id_vehicule", "num_veh", "catv"},
            required_columns={"Num_Acc", "num_veh", "catv"},
        )
        for frame in (users, vehicles):
            frame["Num_Acc"] = frame["Num_Acc"].astype("string").str.strip()
            frame["num_veh"] = frame["num_veh"].astype("string").str.strip()
        users = users[users["Num_Acc"].isin(accident_ids)].copy()
        vehicles = vehicles[vehicles["Num_Acc"].isin(accident_ids)].copy()
        vehicles["vehicle_code"] = _clean_code(vehicles["catv"]).fillna("-1")
        vehicle_lookup = vehicles[
            ["Num_Acc", "num_veh", "vehicle_code"]
        ].drop_duplicates(["Num_Acc", "num_veh"])
        users = users.merge(
            vehicle_lookup,
            on=["Num_Acc", "num_veh"],
            how="left",
            validate="many_to_one",
        )
        users["severity_code"] = _clean_code(users["grav"]).fillna("-1")
        if injured_only:
            users = users[users["severity_code"].isin(["2", "3", "4"])].copy()
        users["severity"] = users["severity_code"].map(USER_SEVERITY)
        users["user_category"] = _clean_code(users["catu"]).map(USER_CATEGORY).fillna(
            "Inconnu"
        )
        users["sex"] = _clean_code(users["sexe"]).map(SEX).fillna("Inconnu")
        users["vehicle_code"] = users["vehicle_code"].fillna("-1")
        users["vehicle_type"] = users["vehicle_code"].map(VEHICLE_LABELS).fillna(
            "Véhicule inconnu"
        )
        users["mobility"] = [
            _mobility_group(category, vehicle)
            for category, vehicle in zip(users["user_category"], users["vehicle_code"])
        ]
        users["user_type"] = users["vehicle_type"]
        users.loc[users["user_category"].eq("Piéton"), "user_type"] = "Piéton"
        birth_year = pd.to_numeric(users["an_nais"], errors="coerce")
        users["age"] = year - birth_year
        users.loc[~users["age"].between(0, 110), "age"] = pd.NA
        users["year"] = year
        users["victim_id"] = [f"{year}-{index}" for index in users.index]
        users = users.rename(columns={"Num_Acc": "accident_id"})
        frames.append(
            users[
                [
                    "victim_id", "accident_id", "year", "severity_code",
                    "severity", "age", "sex", "user_category", "vehicle_code",
                    "vehicle_type", "mobility", "user_type",
                ]
            ]
        )
    if not frames:
        return pd.DataFrame(
            columns=[
                "victim_id", "accident_id", "year", "severity_code", "severity",
                "age", "sex", "user_category", "vehicle_code", "vehicle_type",
                "mobility", "user_type",
            ]
        )
    return pd.concat(frames, ignore_index=True).sort_values(
        ["year", "accident_id", "victim_id"]
    ).reset_index(drop=True)


def get_fatalities_by_user_type(
    victims: pd.DataFrame,
    *,
    years: Iterable[int] | int | None = None,
) -> pd.DataFrame:
    """Compte les personnes tuées par année et type d'usager."""
    required = {"victim_id", "year", "severity_code", "user_type"}
    missing = required.difference(victims.columns)
    if missing:
        raise ValueError(f"Colonnes absentes : {sorted(missing)}")
    selected = victims[victims["severity_code"].eq("2")].copy()
    if years is not None:
        requested = (
            {int(years)}
            if isinstance(years, (int, str))
            else {int(y) for y in years}
        )
        selected = selected[selected["year"].isin(requested)]
    return (
        selected.groupby(["year", "user_type"], as_index=False)
        .agg(fatalities=("victim_id", "nunique"))
        .sort_values(["year", "user_type"])
        .reset_index(drop=True)
    )


def export_csv(dataframe: pd.DataFrame, output: str | Path) -> Path:
    """Enregistre un résultat d'analyse en CSV UTF-8 et retourne son chemin."""
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(path, index=False, encoding="utf-8")
    return path
