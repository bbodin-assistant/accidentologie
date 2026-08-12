#!/usr/bin/env python3
"""Exemple complet : télécharge, analyse et crée un rapport pour un territoire."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import matplotlib.pyplot as plt

from accidentologie import (
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


DEFAULT_TERRITORY = Territory(
    "Communauté d'agglomération Royan Atlantique (CARA)",
    (
        "17015", "17021", "17034", "17060", "17064", "17068", "17079",
        "17098", "17119", "17131", "17152", "17155", "17160", "17183",
        "17151", "17452", "17097", "17225", "17228", "17230", "17247",
        "17248", "17306", "17307", "17311", "17333", "17380", "17393",
        "17409", "17421", "17425", "17437", "17461",
    ),
)


def slugify(value: str) -> str:
    normalized = value.casefold().replace("é", "e").replace("è", "e").replace("à", "a")
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")


def save_figure(figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=180, bbox_inches="tight")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--territory-name",
        default=DEFAULT_TERRITORY.name,
        help="nom affiché dans les graphiques et le rapport",
    )
    parser.add_argument(
        "--communes",
        nargs="+",
        default=list(DEFAULT_TERRITORY.communes),
        metavar="CODE_INSEE",
        help="codes INSEE communaux (défaut : communes de la CARA)",
    )
    parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        default=list(range(2005, 2025)),
        help="années à analyser (défaut : 2005 à 2024)",
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
        "--fatality-years",
        nargs="+",
        type=int,
        help="années du graphique des tués (défaut : deux dernières années analysées)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    territory = Territory(args.territory_name, args.communes)
    years = sorted(set(args.years))
    slug = slugify(territory.name)
    result_dir = args.output_dir / slug
    csv_dir = result_dir / "csv"
    plot_dir = result_dir / "plots"

    if args.download or args.force_download:
        downloaded = download_csv_files(
            years,
            data_dir=args.data_dir,
            force=args.force_download,
        )
        print(f"CSV téléchargés : {len(downloaded)}")

    accidents = get_dataframe(
        years=years,
        communes=territory.communes,
        data_dir=args.data_dir,
    )
    if accidents.empty:
        raise SystemExit(f"Aucun accident trouvé pour {territory.name}")
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
            title=f"Accidents géolocalisés — {territory.name}",
        )
        figures.append(ax.figure)
        save_figure(ax.figure, plot_dir / "carte_gravite.png")
        plot_severity_map(accidents, output=result_dir / "carte_interactive.html")

    if not args.skip_clustering:
        try:
            clustering = cluster_victims(victims)
        except ValueError as error:
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
