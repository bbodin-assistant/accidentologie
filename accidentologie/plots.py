"""Visualisations à partir du DataFrame canonique d'accidentologie."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

import folium
import matplotlib.pyplot as plt
import pandas as pd
from folium.plugins import MarkerCluster


SEVERITY_ORDER = [
    "Léger",
    "Grave non mortel",
    "Mortel",
    "Indemne seulement",
    "Inconnue",
]
SEVERITY_COLORS = {
    "Léger": "#FFD800",
    "Grave non mortel": "#F28C00",
    "Mortel": "#D00000",
    "Indemne seulement": "#6BAED6",
    "Inconnue": "#999999",
}


def _require_columns(dataframe: pd.DataFrame, columns: set[str]) -> None:
    missing = sorted(columns.difference(dataframe.columns))
    if missing:
        raise ValueError(
            "Colonnes manquantes dans le DataFrame : " + ", ".join(missing)
        )


def plot_accident_per_year(
    dataframe: pd.DataFrame,
    *,
    ax: Any | None = None,
    stacked: bool = True,
    title: str = "Nombre d'accidents par année et gravité",
) -> Any:
    """Trace le nombre d'accidents par année et gravité et retourne l'axe Matplotlib."""
    _require_columns(dataframe, {"accident_id", "year", "severity"})
    if dataframe.empty:
        raise ValueError("Le DataFrame ne contient aucun accident à représenter")
    counts = (
        dataframe.groupby(["year", "severity"])["accident_id"]
        .nunique()
        .unstack(fill_value=0)
    )
    columns = [
        severity
        for severity in SEVERITY_ORDER
        if severity in counts and counts[severity].sum() > 0
    ]
    counts = counts.reindex(columns=columns)
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 5.5))
    counts.plot(
        kind="bar",
        stacked=stacked,
        ax=ax,
        color=[SEVERITY_COLORS[column] for column in columns],
        edgecolor="white",
        linewidth=0.35,
        width=0.76,
    )
    ax.set_title(title)
    ax.set_xlabel("Année")
    ax.set_ylabel("Nombre d'accidents")
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    ax.legend(title="Gravité", frameon=False)
    ax.tick_params(axis="x", rotation=0)
    return ax


def _style_table(table: Any) -> None:
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    for (row, column), cell in table.get_celld().items():
        cell.set_edgecolor("#D1CCC2")
        cell.set_linewidth(0.45)
        if row == 0:
            cell.set_facecolor("#17324D")
            cell.get_text().set_color("white")
            cell.get_text().set_fontweight("bold")
        else:
            cell.set_facecolor("white" if row % 2 else "#ECE8DF")
            if column == 0:
                cell.get_text().set_ha("left")


def plot_vehicle_severity_table(
    table_data: pd.DataFrame,
    *,
    ax: Any | None = None,
    title: str = "Accidents par véhicule impliqué et gravité",
    max_rows: int = 18,
) -> Any:
    """Affiche le résultat de :func:`get_vehicle_severity_table` en tableau."""
    _require_columns(table_data, {"vehicle_type", "severity", "accident_count"})
    pivot = table_data.pivot_table(
        index="vehicle_type",
        columns="severity",
        values="accident_count",
        aggfunc="sum",
        fill_value=0,
    )
    severity_columns = [severity for severity in SEVERITY_ORDER if severity in pivot]
    pivot = pivot[severity_columns]
    pivot["Total"] = pivot.sum(axis=1)
    pivot = pivot.sort_values("Total", ascending=False).head(max_rows)
    display = pivot.reset_index()
    display.columns = ["Type de véhicule", *severity_columns, "Total"]
    if ax is None:
        _, ax = plt.subplots(figsize=(11.7, 8.3))
    ax.axis("off")
    ax.set_title(title, fontsize=16, fontweight="bold", color="#17324D", pad=18)
    widths = [0.44] + [0.52 / max(1, len(display.columns) - 1)] * (
        len(display.columns) - 1
    )
    rendered = ax.table(
        cellText=display.values,
        colLabels=display.columns,
        cellLoc="center",
        colLoc="center",
        colWidths=widths,
        bbox=[0, 0.02, 1, 0.90],
    )
    _style_table(rendered)
    return ax


def plot_fatalities_by_user_type(
    table_data: pd.DataFrame,
    *,
    ax: Any | None = None,
    title: str = "Personnes tuées par type d'usager",
) -> Any:
    """Trace les décès à partir de :func:`get_fatalities_by_user_type`."""
    _require_columns(table_data, {"year", "user_type", "fatalities"})
    if table_data.empty:
        raise ValueError("Aucune personne tuée dans la sélection")
    pivot = table_data.pivot_table(
        index="user_type", columns="year", values="fatalities", fill_value=0
    )
    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index]
    if ax is None:
        _, ax = plt.subplots(figsize=(11, 6.5))
    color_count = len(pivot.columns)
    colors = [
        plt.cm.Blues(0.45 + 0.45 * index / max(1, color_count - 1))
        for index in range(color_count)
    ]
    pivot.plot(kind="bar", ax=ax, color=colors)
    ax.set_title(title)
    ax.set_xlabel("Type d'usager")
    ax.set_ylabel("Personnes tuées")
    ax.tick_params(axis="x", rotation=25)
    for label in ax.get_xticklabels():
        label.set_horizontalalignment("right")
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    ax.legend(title="Année", frameon=False)
    return ax


def plot_severity_map_static(
    dataframe: pd.DataFrame,
    *,
    ax: Any | None = None,
    title: str = "Carte des accidents corporels",
) -> Any:
    """Trace une carte statique, adaptée à l'intégration dans un PDF."""
    _require_columns(dataframe, {"latitude", "longitude", "severity"})
    mapped = dataframe[
        dataframe["latitude"].notna() & dataframe["longitude"].notna()
    ]
    if mapped.empty:
        raise ValueError("Aucun accident ne possède de coordonnées valides")
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 8))
    styles = [
        ("Léger", "o", "#FFD800", 14, "#8F7900"),
        ("Grave non mortel", "D", "#F28C00", 30, "#8A4B00"),
        ("Mortel", "*", "#D00000", 100, "#8A0000"),
    ]
    for severity, marker, color, size, edge in styles:
        subset = mapped[mapped["severity"].eq(severity)]
        if subset.empty:
            continue
        ax.scatter(
            subset["longitude"], subset["latitude"], marker=marker, s=size,
            c=color, edgecolors=edge, linewidths=0.55,
            alpha=0.65 if severity == "Léger" else 0.85,
            label=f"{severity} ({len(subset)})",
        )
    ax.set_title(title)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(alpha=0.20)
    ax.legend(frameon=False)
    return ax


def plot_cluster_profiles(
    profiles: pd.DataFrame,
    *,
    ax: Any | None = None,
    title: str = "Profils de victimes",
) -> Any:
    """Trace le taux de victimes hospitalisées ou tuées de chaque cluster."""
    _require_columns(
        profiles, {"cluster", "profile", "serious_or_killed_rate_pct", "victims"}
    )
    ordered = profiles.sort_values("serious_or_killed_rate_pct")
    if ax is None:
        _, ax = plt.subplots(figsize=(11, 6.5))
    bars = ax.barh(
        [f"C{row.cluster} — {row.profile}" for row in ordered.itertuples()],
        ordered["serious_or_killed_rate_pct"],
        color="#315B78",
    )
    ax.bar_label(
        bars,
        labels=[
            f"{rate:.1f} % — {count} victimes"
            for rate, count in zip(
                ordered["serious_or_killed_rate_pct"], ordered["victims"]
            )
        ],
        padding=3,
        fontsize=8,
    )
    ax.set_title(title)
    ax.set_xlabel("Part des victimes hospitalisées ou tuées")
    ax.set_xlim(0, ordered["serious_or_killed_rate_pct"].max() + 18)
    ax.grid(axis="x", alpha=0.25)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", labelsize=8)
    return ax


def plot_clustering_diagnostic(
    diagnostics: pd.DataFrame,
    *,
    ax: Any | None = None,
    title: str = "Choix du nombre de profils",
) -> Any:
    """Trace silhouette, admissibilité et modèle retenu pour le clustering."""
    _require_columns(
        diagnostics,
        {"number_clusters", "gower_silhouette", "eligible", "selected"},
    )
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 5.8))
    ax.plot(
        diagnostics["number_clusters"], diagnostics["gower_silhouette"],
        color="#F28C00", marker="o", label="Silhouette de Gower",
    )
    eligible = diagnostics[diagnostics["eligible"]]
    ax.scatter(
        eligible["number_clusters"], eligible["gower_silhouette"],
        color="#5AA469", s=65, zorder=4, label="Admissible",
    )
    selected = diagnostics[diagnostics["selected"]]
    ax.scatter(
        selected["number_clusters"], selected["gower_silhouette"],
        color="#D00000", marker="*", s=190, zorder=5, label="Retenu",
    )
    ax.set_title(title)
    ax.set_xlabel("Nombre de groupes")
    ax.set_ylabel("Score de silhouette")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False)
    return ax


def _marker_icon(severity: str) -> folium.DivIcon:
    if severity == "Mortel":
        marker = (
            '<div style="font-size:28px;line-height:24px;color:#d00000;'
            'text-shadow:0 0 2px white,0 0 2px white;">★</div>'
        )
        size, anchor = (28, 28), (14, 14)
    elif severity == "Grave non mortel":
        marker = (
            '<div style="width:15px;height:15px;background:#f28c00;'
            'border:2px solid #8a4b00;transform:rotate(45deg);'
            'box-shadow:0 0 2px white;"></div>'
        )
        size, anchor = (19, 19), (9, 9)
    else:
        marker = (
            '<div style="width:13px;height:13px;background:#ffd800;'
            'border:2px solid #8f7900;border-radius:50%;'
            'box-shadow:0 0 2px white;"></div>'
        )
        size, anchor = (17, 17), (8, 8)
    return folium.DivIcon(html=marker, icon_size=size, icon_anchor=anchor)


def _popup(row: pd.Series) -> str:
    date = row["date"].strftime("%d/%m/%Y") if pd.notna(row["date"]) else str(row["year"])
    address = html.escape(str(row["address"])) if pd.notna(row["address"]) else "Non renseignée"
    vehicles = html.escape(str(row["vehicle_types"])) if pd.notna(row["vehicle_types"]) else "Non renseignés"
    time = html.escape(str(row["time"])) if pd.notna(row["time"]) else "heure inconnue"
    return f"""
    <div style="font-family:Arial,sans-serif;font-size:13px;min-width:260px">
      <strong>{html.escape(str(row['severity']))}</strong><br>
      <b>Date :</b> {date}, {time}<br>
      <b>Commune INSEE :</b> {html.escape(str(row['commune_code']))}<br>
      <b>Adresse :</b> {address}<br>
      <b>Véhicules :</b> {vehicles}<br>
      <b>Personnes tuées :</b> {int(row['number_killed'])}<br>
      <b>Identifiant :</b> {html.escape(str(row['accident_id']))}
    </div>
    """


def plot_severity_map(
    dataframe: pd.DataFrame,
    *,
    output: str | Path | None = None,
    tiles: str = "CartoDB positron",
    cluster: bool = True,
    max_points: int | None = 20_000,
) -> folium.Map:
    """Crée une carte Folium des accidents géolocalisés et la retourne.

    Les accidents mortels sont des étoiles rouges, les graves non mortels des
    losanges orange et les légers des ronds jaunes. Si ``output`` est fourni,
    la carte est également enregistrée dans un fichier HTML.
    """
    required = {
        "accident_id",
        "year",
        "date",
        "time",
        "commune_code",
        "address",
        "latitude",
        "longitude",
        "severity",
        "number_killed",
        "vehicle_types",
    }
    _require_columns(dataframe, required)
    mapped = dataframe[
        dataframe["latitude"].notna() & dataframe["longitude"].notna()
    ].copy()
    if mapped.empty:
        raise ValueError("Aucun accident du DataFrame ne possède de coordonnées valides")
    if max_points is not None and len(mapped) > max_points:
        raise ValueError(
            f"La carte contiendrait {len(mapped):,} points. Filtrez les années/communes "
            f"ou augmentez explicitement max_points (limite actuelle : {max_points:,})."
        )

    accident_map = folium.Map(
        location=[mapped["latitude"].median(), mapped["longitude"].median()],
        zoom_start=10,
        tiles=tiles,
        control_scale=True,
    )
    layer: Any
    if cluster:
        layer = MarkerCluster(
            name=f"Accidents ({len(mapped)})",
            options={"disableClusteringAtZoom": 15, "maxClusterRadius": 45},
        ).add_to(accident_map)
    else:
        layer = accident_map
    for _, row in mapped.iterrows():
        folium.Marker(
            location=[row["latitude"], row["longitude"]],
            icon=_marker_icon(str(row["severity"])),
            tooltip=f"{row['year']} — {row['commune_code']} — {row['severity']}",
            popup=folium.Popup(_popup(row), max_width=420),
        ).add_to(layer)

    accident_map.fit_bounds(
        [
            [mapped["latitude"].min(), mapped["longitude"].min()],
            [mapped["latitude"].max(), mapped["longitude"].max()],
        ],
        padding=(20, 20),
    )
    folium.LayerControl(collapsed=False).add_to(accident_map)
    if output is not None:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        accident_map.save(output_path)
    return accident_map
