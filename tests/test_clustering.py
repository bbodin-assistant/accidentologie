from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from accidentologie import ClusteringError, cluster_victims


def victims_fixture(size: int = 120) -> pd.DataFrame:
    group = np.arange(size) % 4
    return pd.DataFrame(
        {
            "victim_id": [f"V{index}" for index in range(size)],
            "severity_code": np.where(group == 0, "3", "4"),
            "age": 18 + group * 18 + np.arange(size) % 5,
            "sex": np.where(group % 2 == 0, "Femme", "Homme"),
            "user_category": np.where(group == 3, "Piéton", "Conducteur"),
            "mobility": np.array(["Vélo / VAE", "Voiture / voiturette", "EDP", "Piéton"])[group],
        }
    )


class ClusteringTests(unittest.TestCase):
    def test_stability_uses_a_true_subsample(self) -> None:
        result = cluster_victims(
            victims_fixture(),
            min_clusters=2,
            max_clusters=4,
            min_cluster_share=0,
            min_stability_ari=0,
            stability_repetitions=3,
            stability_fraction=0.75,
            sample_size=120,
        )
        self.assertTrue((result.diagnostics["stability_sample_size"] == 90).all())
        self.assertTrue((result.diagnostics["stability_repetitions"] == 3).all())

    def test_memory_guard_is_explicit(self) -> None:
        with self.assertRaisesRegex(ClusteringError, "max_victims=50"):
            cluster_victims(victims_fixture(), max_clusters=4, max_victims=50)

    def test_description_does_not_claim_population_risk(self) -> None:
        self.assertIn("ne mesure pas un risque", cluster_victims.__doc__ or "")


if __name__ == "__main__":
    unittest.main()
