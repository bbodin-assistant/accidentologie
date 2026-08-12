from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from accidentologie import (
    plot_accident_per_year,
    plot_severity_map,
    plot_severity_map_static,
    plot_vehicle_severity_table,
    save_pdf_report,
)


class PlotReportTests(unittest.TestCase):
    def tearDown(self) -> None:
        plt.close("all")

    def test_annual_plot_marks_the_methodology_break(self) -> None:
        dataframe = pd.DataFrame(
            {
                "accident_id": ["A", "B"],
                "year": [2017, 2018],
                "severity": ["Blessé hospitalisé", "Blessé hospitalisé"],
            }
        )
        ax = plot_accident_per_year(dataframe)
        self.assertTrue(any(line.get_linestyle() == "--" for line in ax.lines))

    def test_folium_map_accepts_a_minimal_dataframe_and_has_a_legend(self) -> None:
        dataframe = pd.DataFrame(
            {
                "latitude": [48.86, 48.861],
                "longitude": [2.34, 2.341],
                "severity": ["Inconnue", "Indemne seulement"],
            }
        )
        rendered = plot_severity_map(dataframe, cluster=False).get_root().render()
        self.assertIn("Gravité maximale", rendered)
        self.assertIn("background:#999", rendered)
        self.assertIn("background:#6baed6", rendered)

    def test_static_map_can_be_rendered_offline_without_axes(self) -> None:
        dataframe = pd.DataFrame(
            {
                "latitude": [48.86],
                "longitude": [2.34],
                "severity": ["Blessé hospitalisé"],
            }
        )
        ax = plot_severity_map_static(dataframe, basemap=False)
        self.assertFalse(ax.axison)
        self.assertEqual(len(ax.collections), 1)

    def test_vehicle_table_is_not_truncated_by_default(self) -> None:
        rows = [
            {"vehicle_type": f"Type {index}", "severity": "Léger", "accident_count": 1}
            for index in range(25)
        ]
        ax = plot_vehicle_severity_table(pd.DataFrame(rows))
        table = next(iter(ax.tables))
        self.assertEqual(max(row for row, _ in table.get_celld()), 25)

    def test_pdf_export_restores_figure_size(self) -> None:
        figure, _ = plt.subplots(figsize=(4, 3))
        original = tuple(figure.get_size_inches())
        with TemporaryDirectory() as directory:
            path = save_pdf_report([figure], Path(directory) / "report.pdf")
            self.assertGreater(path.stat().st_size, 0)
        self.assertEqual(tuple(figure.get_size_inches()), original)


if __name__ == "__main__":
    unittest.main()
