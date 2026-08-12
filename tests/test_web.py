from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import pandas as pd

from accidentologie import build_web_map


class WebMapTests(unittest.TestCase):
    def test_years_are_discovered_and_view_fits_distant_points(self) -> None:
        dataframe = pd.DataFrame(
            {
                "has_coordinates": [True, True],
                "longitude": [-1.03, 2.34],
                "latitude": [45.63, 48.86],
                "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
                "severity": ["Blessé hospitalisé", "Inconnue"],
                "commune_code": ["17306", "75101"],
                "accident_id": ["A", "B"],
            }
        )
        with TemporaryDirectory() as directory:
            with (
                patch("accidentologie.web._normalize_years", return_value=[2024]) as normalize,
                patch("accidentologie.web.get_dataframe", return_value=dataframe),
            ):
                index = build_web_map(
                    years=None,
                    data_dir=Path(directory) / "data",
                    output_dir=Path(directory) / "site",
                )
            manifest = json.loads((index.parent / "manifest.json").read_text())
            html = index.read_text()
        normalize.assert_called_once()
        self.assertLessEqual(manifest["view"]["zoom"], 6)
        self.assertEqual(manifest["view"]["bounds"], [[-1.03, 45.63], [2.34, 48.86]])
        self.assertIn('data-severity="-1"', html)
        self.assertIn("Blessé hospitalisé", html)


if __name__ == "__main__":
    unittest.main()
