"""
Math OCR: formula image → LaTeX. Uses pix2tex when available.
"""

from __future__ import annotations

from pathlib import Path


def run_math_ocr_pix2tex(image_path: str | Path) -> str:
    """Run pix2tex (LaTeX-OCR) on formula image. Returns LaTeX string."""
    try:
        from pix2tex.cli import LatexOCR
        model = LatexOCR(arguments=None)
        return model(str(image_path)) or ""
    except Exception:
        return ""
