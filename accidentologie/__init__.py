"""API publique pour explorer les données françaises d'accidentologie BAAC."""

from importlib.metadata import PackageNotFoundError, version

from .analysis import (
    export_csv,
    get_accidents_per_year,
    get_fatalities_by_user_type,
    get_vehicle_severity_table,
    get_victim_dataframe,
)
from .clustering import ClusterResult, ClusteringError, cluster_victims
from .data import get_dataframe
from .download import ANALYSIS_TABLES, TABLES, console_progress, download_csv_files
from .plots import (
    plot_accident_per_year,
    plot_cluster_profiles,
    plot_clustering_diagnostic,
    plot_fatalities_by_user_type,
    plot_mobility_severity,
    plot_monthly_seasonality,
    plot_severity_map,
    plot_severity_map_static,
    plot_victim_age_pyramid,
    plot_vehicle_severity_table,
    plot_weekday_hour_heatmap,
)
from .report import save_pdf_report
from .territories import Territory
from .web import build_web_map

__all__ = [
    "ClusterResult",
    "ClusteringError",
    "ANALYSIS_TABLES",
    "TABLES",
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
    "plot_mobility_severity",
    "plot_monthly_seasonality",
    "plot_severity_map",
    "plot_severity_map_static",
    "plot_victim_age_pyramid",
    "plot_vehicle_severity_table",
    "plot_weekday_hour_heatmap",
    "save_pdf_report",
]

try:
    __version__ = version("accidentologie")
except PackageNotFoundError:  # exécution directe depuis une copie des sources
    __version__ = "0+unknown"
