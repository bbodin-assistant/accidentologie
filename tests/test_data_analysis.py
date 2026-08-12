from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from accidentologie.analysis import USER_CATEGORY, _mobility_group, get_vehicle_severity_table
from accidentologie.data import SEVERITY_LABELS, _read_baac
from accidentologie.territories import Territory


class DataAnalysisTests(unittest.TestCase):
    def test_historical_category_four_is_a_pedestrian(self) -> None:
        self.assertEqual(USER_CATEGORY["4"], "Piéton")
        self.assertEqual(_mobility_group(USER_CATEGORY["4"], "7"), "Piéton")

    def test_official_hospitalized_label_is_preserved(self) -> None:
        self.assertEqual(SEVERITY_LABELS["3"], "Blessé hospitalisé")

    def test_vehicle_table_does_not_require_an_unused_year(self) -> None:
        dataframe = pd.DataFrame(
            {
                "accident_id": ["A", "B"],
                "severity": ["Léger", "Mortel"],
                "vehicle_types": ["Bicyclette", "Voiture particulière"],
            }
        )
        result = get_vehicle_severity_table(dataframe)
        self.assertEqual(result["accident_count"].sum(), 2)

    def test_csv_schema_error_names_missing_columns(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "usagers-2024.csv"
            path.write_text("Num_Acc,other\nA,x\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "grav"):
                _read_baac(
                    path,
                    2024,
                    {"Num_Acc", "grav"},
                    required_columns={"Num_Acc", "grav"},
                )

    def test_territory_is_loaded_from_geojson(self) -> None:
        payload = {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "properties": {"code": "75101"}, "geometry": None},
                {"type": "Feature", "properties": {"code": "17306"}, "geometry": None},
            ],
        }
        with TemporaryDirectory() as directory:
            path = Path(directory) / "territoire.geojson"
            path.write_text(json.dumps(payload), encoding="utf-8")
            territory = Territory.from_geojson(path, name="Test")
        self.assertEqual(territory.communes, ("75101", "17306"))


if __name__ == "__main__":
    unittest.main()
