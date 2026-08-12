#!/usr/bin/env python3
"""Exemple complet : télécharge, analyse et crée un rapport pour un territoire."""

from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path

import matplotlib.pyplot as plt

from accidentologie import (
    ANALYSIS_TABLES,
    ClusteringError,
    Territory,
    cluster_victims,
    download_csv_files,
    export_csv,
    get_accidents_per_year,
    get_dataframe,
    get_fatalities_by_user_type,
    get_vehicle_severity_table,
    get_victim_dataframe,
    plot_accident_per_year,
    plot_cluster_profiles,
    plot_clustering_diagnostic,
    plot_fatalities_by_user_type,
    plot_severity_map,
    plot_severity_map_static,
    plot_vehicle_severity_table,
    save_pdf_report,
)


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold()).encode(
        "ascii", "ignore"
    ).decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")


def save_figure(figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=180, bbox_inches="tight")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--territory-name",
        default=None,
        help="nom affiché dans les graphiques et le rapport",
    )
    territory = parser.add_mutually_exclusive_group(required=True)
    territory.add_argument(
        "--communes",
        nargs="+",
        metavar="CODE_INSEE",
        help="codes INSEE communaux",
    )
    territory.add_argument(
        "--territory-geojson",
        type=Path,
        help="GeoJSON dont les propriétés `code` définissent les communes",
    )
    parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        default=None,
        help="années à analyser (défaut : toutes les années locales)",
    )
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument(
        "--download",
        action="store_true",
        help="télécharger les CSV manquants avant l'analyse",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="retélécharger les CSV même s'ils existent",
    )
    parser.add_argument(
        "--skip-clustering",
        action="store_true",
        help="ne pas calculer les profils de victimes",
    )
    parser.add_argument(
        "--cluster-max-clusters",
        type=int,
        default=20,
        help="nombre maximal de profils comparés",
    )
    parser.add_argument(
        "--cluster-max-victims",
        type=int,
        default=5000,
        help="garde mémoire du clustering hiérarchique",
    )
    parser.add_argument(
        "--vehicle-table-max-rows",
        type=int,
        default=None,
        help="limiter explicitement le nombre de types de véhicules dans le PDF",
    )
    parser.add_argument(
        "--no-basemap",
        action="store_true",
        help="ne pas charger de fond cartographique pour la carte statique",
    )
    parser.add_argument(
        "--no-interactive-map",
        action="store_true",
        help="ne pas produire la carte Folium",
    )
    parser.add_argument(
        "--interactive-map-max-points",
        type=int,
        default=20_000,
        help="nombre maximal de marqueurs Folium",
    )
    parser.add_argument(
        "--fatality-years",
        nargs="+",
        type=int,
        help="années du graphique des tués (défaut : deux dernières années analysées)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.territory_geojson:
        territory = Territory.from_geojson(
            args.territory_geojson,
            name=args.territory_name,
        )
    else:
        territory = Territory(
            args.territory_name or "Territoire sélectionné",
            args.communes,
        )
    slug = slugify(territory.name)
    result_dir = args.output_dir / slug
    csv_dir = result_dir / "csv"
    plot_dir = result_dir / "plots"

    if args.download or args.force_download:
        downloaded = download_csv_files(
            args.years,
            data_dir=args.data_dir,
            tables=ANALYSIS_TABLES,
            force=args.force_download,
        )
        print(f"CSV téléchargés : {len(downloaded)}")

    accidents = get_dataframe(
        years=args.years,
        communes=territory.communes,
        data_dir=args.data_dir,
    )
    if accidents.empty:
        raise SystemExit(f"Aucun accident trouvé pour {territory.name}")
    years = sorted(int(year) for year in accidents["year"].unique())
    accident_counts = get_accidents_per_year(accidents)
    vehicle_table = get_vehicle_severity_table(accidents)
    victims = get_victim_dataframe(
        years=years,
        communes=territory.communes,
        data_dir=args.data_dir,
    )
    fatalities = get_fatalities_by_user_type(victims)
    fatality_years = (
        sorted(set(args.fatality_years))
        if args.fatality_years
        else years[-min(2, len(years)) :]
    )
    fatalities_for_plot = fatalities[fatalities["year"].isin(fatality_years)]

    export_csv(accidents, csv_dir / "accidents.csv")
    export_csv(accident_counts, csv_dir / "accidents_par_annee_gravite.csv")
    export_csv(vehicle_table, csv_dir / "accidents_par_vehicule_gravite.csv")
    export_csv(victims, csv_dir / "usagers.csv")
    export_csv(fatalities, csv_dir / "tues_par_type_usager.csv")

    figures = []
    ax = plot_accident_per_year(
        accidents,
        title=f"Accidents par année et gravité — {territory.name}",
    )
    figures.append(ax.figure)
    save_figure(ax.figure, plot_dir / "accidents_par_annee.png")

    ax = plot_vehicle_severity_table(
        vehicle_table,
        max_rows=args.vehicle_table_max_rows,
        title=f"Accidents par véhicule et gravité — {territory.name}",
    )
    figures.append(ax.figure)
    save_figure(ax.figure, plot_dir / "vehicules_par_gravite.png")

    if not fatalities_for_plot.empty:
        ax = plot_fatalities_by_user_type(
            fatalities_for_plot,
            title=f"Personnes tuées par type d'usager — {territory.name}",
        )
        figures.append(ax.figure)
        save_figure(ax.figure, plot_dir / "tues_par_type_usager.png")

    if accidents["has_coordinates"].any():
        ax = plot_severity_map_static(
            accidents,
            basemap=not args.no_basemap,
            title=f"Accidents géolocalisés — {territory.name}",
        )
        figures.append(ax.figure)
        save_figure(ax.figure, plot_dir / "carte_gravite.png")
        if not args.no_interactive_map:
            plot_severity_map(
                accidents,
                output=result_dir / "carte_interactive.html",
                max_points=args.interactive_map_max_points,
            )

    if not args.skip_clustering:
        try:
            clustering = cluster_victims(
                victims,
                max_clusters=args.cluster_max_clusters,
                max_victims=args.cluster_max_victims,
            )
        except ClusteringError as error:
            print(f"Clustering ignoré : {error}")
        else:
            export_csv(clustering.profiles, csv_dir / "clusters_profils.csv")
            export_csv(clustering.victims, csv_dir / "usagers_avec_cluster.csv")
            export_csv(clustering.diagnostics, csv_dir / "clusters_diagnostic.csv")

            ax = plot_cluster_profiles(
                clustering.profiles,
                title=f"Profils de victimes — {territory.name}",
            )
            figures.append(ax.figure)
            save_figure(ax.figure, plot_dir / "clusters_profils.png")

            ax = plot_clustering_diagnostic(
                clustering.diagnostics,
                title=f"Choix du nombre de profils — {territory.name}",
            )
            figures.append(ax.figure)
            save_figure(ax.figure, plot_dir / "clusters_diagnostic.png")

    report = save_pdf_report(
        figures,
        result_dir / "rapport.pdf",
        title=f"Rapport d'accidentologie — {territory.name}",
        metadata={
            "Subject": f"Accidents corporels {years[0]}–{years[-1]}",
        },
    )
    plt.close("all")
    print(f"Territoire : {territory.name} ({len(territory.communes)} commune(s))")
    print(f"Accidents analysés : {len(accidents)}")
    print(f"Rapport : {report.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
