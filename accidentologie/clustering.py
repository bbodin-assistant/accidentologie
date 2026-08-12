"""Clustering des profils de victimes sur variables mixtes."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import pdist, squareform
from sklearn.metrics import adjusted_rand_score, silhouette_score


@dataclass(slots=True)
class ClusterResult:
    """Résultats complets d'un clustering de victimes."""

    profiles: pd.DataFrame
    victims: pd.DataFrame
    diagnostics: pd.DataFrame
    selected_clusters: int


def _dominant(series: pd.Series) -> str:
    modes = series.dropna().mode()
    return str(modes.iloc[0]) if not modes.empty else "Inconnu"


def _dominant_share(series: pd.Series) -> float:
    frequencies = series.dropna().value_counts(normalize=True)
    return float(frequencies.iloc[0] * 100) if not frequencies.empty else 0.0


def cluster_victims(
    victims: pd.DataFrame,
    *,
    min_clusters: int = 2,
    max_clusters: int = 20,
    min_cluster_share: float = 0.02,
    min_stability_ari: float = 0.70,
    stability_repetitions: int = 5,
    sample_size: int = 1200,
    random_state: int = 42,
) -> ClusterResult:
    """Segmente les victimes avec une distance de Gower et un lien complet.

    La solution retenue maximise la silhouette parmi les solutions respectant la
    taille minimale de groupe et le seuil de stabilité ARI.
    """
    required = {
        "victim_id", "severity_code", "age", "sex", "user_category", "mobility"
    }
    missing = required.difference(victims.columns)
    if missing:
        raise ValueError(f"Colonnes absentes : {sorted(missing)}")
    victims = victims[victims["severity_code"].isin(["2", "3", "4"])].copy()
    if len(victims) < max(30, max_clusters + 1):
        raise ValueError(
            f"Clustering impossible avec seulement {len(victims)} victimes blessées/tuées"
        )
    if not 2 <= min_clusters <= max_clusters < len(victims):
        raise ValueError("La plage du nombre de clusters est invalide")

    categorical = ["sex", "user_category", "mobility"]
    median_age = victims["age"].median()
    age = victims["age"].fillna(40 if pd.isna(median_age) else median_age).to_numpy(
        dtype=float
    )
    age_distance = pdist((age / max(float(np.ptp(age)), 1.0))[:, None], "cityblock")
    category_codes = np.column_stack(
        [pd.Categorical(victims[column].astype(str)).codes for column in categorical]
    )
    category_distance = pdist(category_codes, "hamming") * len(categorical)
    gower_condensed = (age_distance + category_distance) / (1 + len(categorical))
    gower_matrix = squareform(gower_condensed)
    hierarchy = linkage(gower_condensed, method="complete")
    rng = np.random.default_rng(random_state)
    silhouette_sample = np.sort(
        rng.choice(len(victims), min(2000, len(victims)), replace=False)
    )
    sampled_distances = gower_matrix[np.ix_(silhouette_sample, silhouette_sample)]

    labels_by_count: dict[int, np.ndarray] = {}
    rows = []
    for count in range(min_clusters, max_clusters + 1):
        labels = fcluster(hierarchy, t=count, criterion="maxclust")
        actual_count = len(np.unique(labels))
        if actual_count < 2:
            continue
        labels_by_count[count] = labels
        sizes = np.bincount(labels)[1:]
        sampled_labels = labels[silhouette_sample]
        rows.append(
            {
                "number_clusters": count,
                "actual_clusters": actual_count,
                "gower_silhouette": silhouette_score(
                    sampled_distances, sampled_labels, metric="precomputed"
                ),
                "smallest_cluster_size": int(sizes.min()),
                "smallest_cluster_share_pct": sizes.min() / len(victims) * 100,
            }
        )

    stability: dict[int, list[float]] = {count: [] for count in labels_by_count}
    for _ in range(stability_repetitions):
        sample = np.sort(rng.choice(len(victims), min(sample_size, len(victims)), False))
        distances = gower_matrix[np.ix_(sample, sample)]
        sample_hierarchy = linkage(squareform(distances, checks=False), method="complete")
        for count, labels in labels_by_count.items():
            sample_labels = fcluster(sample_hierarchy, t=count, criterion="maxclust")
            stability[count].append(adjusted_rand_score(labels[sample], sample_labels))

    diagnostics = pd.DataFrame(rows)
    diagnostics["mean_stability_ari"] = diagnostics["number_clusters"].map(
        lambda count: float(np.mean(stability[int(count)]))
    )
    diagnostics["stability_ari_std"] = diagnostics["number_clusters"].map(
        lambda count: float(np.std(stability[int(count)]))
    )
    diagnostics["eligible"] = (
        diagnostics["smallest_cluster_share_pct"].ge(min_cluster_share * 100)
        & diagnostics["mean_stability_ari"].ge(min_stability_ari)
    )
    eligible = diagnostics[diagnostics["eligible"]]
    if eligible.empty:
        raise ValueError(
            "Aucune solution ne respecte les seuils de taille et de stabilité ; "
            "élargissez le territoire ou assouplissez explicitement les seuils."
        )
    best_count = int(
        eligible.sort_values(
            ["gower_silhouette", "number_clusters"], ascending=[False, True]
        ).iloc[0]["number_clusters"]
    )
    clustered = victims.copy()
    clustered["raw_cluster"] = labels_by_count[best_count]
    profiles = clustered.groupby("raw_cluster", as_index=False).agg(
        victims=("victim_id", "size"),
        median_age=("age", "median"),
        dominant_sex=("sex", _dominant),
        dominant_sex_share_pct=("sex", _dominant_share),
        dominant_user_category=("user_category", _dominant),
        dominant_user_category_share_pct=("user_category", _dominant_share),
        dominant_mobility=("mobility", _dominant),
        dominant_mobility_share_pct=("mobility", _dominant_share),
        slightly_injured=("severity_code", lambda values: values.eq("4").sum()),
        hospitalized=("severity_code", lambda values: values.eq("3").sum()),
        killed=("severity_code", lambda values: values.eq("2").sum()),
    )
    profiles["serious_or_killed"] = profiles["hospitalized"] + profiles["killed"]
    profiles["victim_share_pct"] = profiles["victims"] / len(clustered) * 100
    profiles["serious_or_killed_rate_pct"] = (
        profiles["serious_or_killed"] / profiles["victims"] * 100
    )
    profiles["profile"] = (
        profiles["dominant_user_category"] + " — " + profiles["dominant_sex"]
        + " — " + profiles["dominant_mobility"] + " — âge médian "
        + profiles["median_age"].round().astype("Int64").astype("string") + " ans"
    )
    profiles = profiles.sort_values("serious_or_killed", ascending=False).reset_index(drop=True)
    profiles["cluster"] = range(1, len(profiles) + 1)
    cluster_map = profiles.set_index("raw_cluster")["cluster"]
    clustered["cluster"] = clustered["raw_cluster"].map(cluster_map)
    clustered = clustered.drop(columns="raw_cluster").merge(
        profiles[["cluster", "profile"]], on="cluster", how="left", validate="many_to_one"
    )
    profiles = profiles.drop(columns="raw_cluster")
    percentage_columns = [column for column in profiles if column.endswith("_pct")]
    profiles[percentage_columns] = profiles[percentage_columns].round(1)
    diagnostics["selected"] = diagnostics["number_clusters"].eq(best_count)
    numeric = diagnostics.select_dtypes(include="number").columns
    diagnostics[numeric] = diagnostics[numeric].round(4)
    return ClusterResult(profiles, clustered, diagnostics, best_count)
