"""API publique pour explorer les données françaises d'accidentologie BAAC."""

from .analysis import (
    export_csv,
    get_accidents_per_year,
    get_fatalities_by_user_type,
    get_vehicle_severity_table,
    get_victim_dataframe,
)
from .clustering import ClusterResult, cluster_victims
from .data import get_dataframe
from .download import console_progress, download_csv_files
from .plots import (
    plot_accident_per_year,
    plot_cluster_profiles,
    plot_clustering_diagnostic,
    plot_fatalities_by_user_type,
    plot_severity_map,
    plot_severity_map_static,
    plot_vehicle_severity_table,
)
from .report import save_pdf_report
from .territories import CARA, ROYAN, Territory
from .web import build_web_map

__all__ = [
    "CARA",
    "ROYAN",
    "ClusterResult",
    "Territory",
    "cluster_victims",
    "build_web_map",
    "console_progress",
    "download_csv_files",
    "export_csv",
    "get_accidents_per_year",
    "get_dataframe",
    "get_fatalities_by_user_type",
    "get_vehicle_severity_table",
    "get_victim_dataframe",
    "plot_accident_per_year",
    "plot_cluster_profiles",
    "plot_clustering_diagnostic",
    "plot_fatalities_by_user_type",
    "plot_severity_map",
    "plot_severity_map_static",
    "plot_vehicle_severity_table",
    "save_pdf_report",
]

__version__ = "0.1.0"
