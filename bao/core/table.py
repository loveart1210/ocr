"""
Table extraction. Uses PaddleOCR table structure when available; else stub.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def extract_table_paddle(image_path: str | Path) -> list[list[str]]:
    """
    Extract table structure (cells) from image. Returns 2D list of cell texts.
    PaddleOCR table structure if available; else empty.
    """
    try:
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(use_angle_cls=True, lang="vi", use_gpu=False, show_log=False)
        result = ocr.ocr(str(image_path), cls=True)
        if not result or not result[0]:
            return []
        rows: list[list[str]] = []
        for line in result[0]:
            if line and len(line) >= 2:
                text = line[1][0] if isinstance(line[1], (list, tuple)) else str(line[1])
                rows.append([text])
        return rows if rows else []
    except Exception:
        return []


def table_to_markdown(cells: list[list[str]]) -> str:
    """Turn 2D cells into a markdown table string."""
    if not cells:
        return ""
    lines: list[str] = []
    for i, row in enumerate(cells):
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
        if i == 0:
            lines.append("|" + "---|" * len(row))
    return "\n".join(lines)
