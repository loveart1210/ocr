"""
PDF → images and image processing (rotate, crop, denoise).
Uses pdf2image (poppler) and OpenCV + Pillow. Fallback: PyMuPDF in pdf.py.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Sequence


def pdf_to_pages_pdf2image(
    pdf_path: str | Path,
    *,
    output_dir: str | Path | None = None,
    dpi: int = 200,
    fmt: str = "png",
) -> list[str]:
    """Convert PDF to page images via pdf2image (requires poppler-utils)."""
    from pdf2image import convert_from_path
    pdf_path = Path(pdf_path)
    if not pdf_path.exists() or not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    out_dir = Path(output_dir) if output_dir else Path(tempfile.mkdtemp(prefix="bao_"))
    if output_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
    images = convert_from_path(pdf_path, dpi=dpi)
    paths: list[str] = []
    for i, img in enumerate(images):
        p = out_dir / f"page-{i + 1:04d}.{fmt}"
        img.save(str(p))
        paths.append(str(p))
    return paths


def image_rotate(image_path: str | Path, angle: float) -> bytes:
    """Rotate image by angle (degrees), return PNG bytes."""
    from PIL import Image
    img = Image.open(image_path).convert("RGB")
    out = img.rotate(-angle, expand=True)
    import io
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    return buf.getvalue()


def image_crop(image_path: str | Path, box: tuple[int, int, int, int]) -> bytes:
    """Crop image to (left, upper, right, lower), return PNG bytes."""
    from PIL import Image
    img = Image.open(image_path).convert("RGB")
    out = img.crop(box)
    import io
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    return buf.getvalue()


def image_denoise(image_path: str | Path, strength: int = 10) -> bytes:
    """Simple denoise (OpenCV fastNlMeansDenoisingColored), return PNG bytes."""
    import cv2
    import numpy as np
    from PIL import Image
    import io
    img = np.array(Image.open(image_path).convert("RGB"))
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    out = cv2.fastNlMeansDenoisingColored(img_bgr, None, strength, strength, 7, 21)
    out_rgb = cv2.cvtColor(out, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(out_rgb)
    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    return buf.getvalue()
