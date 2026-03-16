"""PDF to page images."""

from __future__ import annotations

import tempfile
from pathlib import Path


def pdf_to_page_images(
    pdf_path: str | Path,
    *,
    output_dir: str | Path | None = None,
    dpi: int = 200,
    image_format: str = "png",
) -> list[str]:
    import fitz
    pdf_file = Path(pdf_path)
    if not pdf_file.exists() or not pdf_file.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_file}")
    out_dir = Path(output_dir) if output_dir else Path(tempfile.mkdtemp(prefix="bao_"))
    if output_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    paths: list[str] = []
    with fitz.open(pdf_file) as doc:
        for i in range(doc.page_count):
            pix = doc.load_page(i).get_pixmap(matrix=matrix, alpha=False)
            p = out_dir / f"page-{i + 1:04d}.{(image_format.strip().lower() or 'png')}"
            pix.save(str(p))
            paths.append(str(p))
    return paths
