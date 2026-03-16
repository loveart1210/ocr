"""
Text OCR (Vietnamese). Uses PaddleOCR when available.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def run_ocr_paddle(image_path: str | Path, lang: str = "vi", use_gpu: bool = False) -> list[dict[str, Any]]:
    """
    Run PaddleOCR on image. Returns list of {text, bbox} for each line.
    """
    try:
        from paddleocr import PaddleOCR
    except ImportError:
        return [{"text": "", "bbox": [0, 0, 0, 0]}]

    ocr = PaddleOCR(use_angle_cls=True, lang=lang, use_gpu=use_gpu, show_log=False)
    result = ocr.ocr(str(image_path), cls=True)
    if not result or not result[0]:
        return [{"text": "", "bbox": [0, 0, 0, 0]}]
    out: list[dict[str, Any]] = []
    for line in result[0]:
        if not line or len(line) < 2:
            continue
        box, (text, _) = line[0], line[1]
        if len(box) >= 4:
            bbox = [min(p[0] for p in box), min(p[1] for p in box), max(p[0] for p in box), max(p[1] for p in box)]
        else:
            bbox = [0, 0, 0, 0]
        out.append({"text": text or "", "bbox": bbox})
    return out if out else [{"text": "", "bbox": [0, 0, 0, 0]}]


def extract_text_from_ocr_result(ocr_result: list[dict[str, Any]]) -> str:
    """Concatenate text lines from run_ocr_paddle result."""
    return "\n".join(item.get("text", "") for item in ocr_result).strip()
