"""Assemblage de figures Matplotlib dans un rapport PDF."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from matplotlib.backends.backend_pdf import PdfPages


def save_pdf_report(
    figures: Iterable[Any],
    output: str | Path,
    *,
    title: str = "Rapport d'accidentologie",
    author: str = "accidentologie",
    metadata: Mapping[str, str] | None = None,
    page_size: tuple[float, float] = (11.69, 8.27),
) -> Path:
    """Enregistre, dans l'ordre, une collection de figures dans un PDF A4 paysage."""
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf_metadata = {"Title": title, "Author": author}
    if metadata:
        pdf_metadata.update(metadata)
    with PdfPages(path, metadata=pdf_metadata) as pdf:
        count = 0
        for figure in figures:
            original_size = tuple(figure.get_size_inches())
            original_layout_engine = figure.get_layout_engine()
            try:
                figure.set_size_inches(*page_size)
                figure.set_layout_engine("tight")
                pdf.savefig(figure)
            finally:
                figure.set_layout_engine(original_layout_engine)
                figure.set_size_inches(*original_size)
            count += 1
    if count == 0:
        path.unlink(missing_ok=True)
        raise ValueError("Le rapport doit contenir au moins une figure")
    return path
