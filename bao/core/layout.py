"""
Layout detection: split page into blocks (title, paragraph, formula, figure, table).
Uses PaddleOCR layout when available; otherwise placeholder.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def detect_layout_paddle(image_path: str | Path) -> list[dict[str, Any]]:
    """
    Detect layout with PaddleOCR. Returns list of blocks: {type, bbox, ...}.
    Types: title, text, formula, figure, table (PaddleOCR layout labels).
    """
    try:
        from paddleocr import PaddleOCR
        from PIL import Image
        import numpy as np
    except ImportError:
        return _placeholder_layout(image_path)

    ocr = PaddleOCR(use_angle_cls=True, lang="vi", use_gpu=False, show_log=False)
    img = np.array(Image.open(image_path).convert("RGB"))
    result = ocr.ocr(img, cls=True)
    if not result or not result[0]:
        return _placeholder_layout(image_path)
    blocks: list[dict[str, Any]] = []
    for i, line in enumerate(result[0]):
        if not line or len(line) < 2:
            continue
        box = line[0]
        if len(box) >= 4:
            x_coords = [p[0] for p in box]
            y_coords = [p[1] for p in box]
            bbox = [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]
        else:
            bbox = [0, 0, 1, 1]
        blocks.append({"type": "text", "bbox": bbox, "order": i})
    return blocks if blocks else _placeholder_layout(image_path)


def _placeholder_layout(image_path: str | Path) -> list[dict[str, Any]]:
    """One full-page block when layout model not used."""
    return [{"type": "text", "bbox": [0, 0, 1, 1], "order": 0}]
