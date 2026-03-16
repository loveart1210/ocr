"""
Client for Colab-hosted model API. When BAO_COLAB_URL is set, pipeline uses this to call
layout/ocr/math/table/figure on Colab instead of running models locally.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def get_colab_url() -> str | None:
    """Base URL of Colab API (from env BAO_COLAB_URL). No trailing slash."""
    url = (os.getenv("BAO_COLAB_URL") or os.getenv("COLAB_MODEL_URL") or "").strip()
    return url.rstrip("/") if url else None


def _post_image(base_url: str, endpoint: str, image_path: str | Path) -> dict[str, Any]:
    """POST image file to base_url + endpoint. Returns JSON body as dict."""
    path = Path(image_path)
    if not path.is_file():
        return {}
    url = f"{base_url}{endpoint}"
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return {}
    try:
        import urllib.request
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "image/png")
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))
    except Exception:
        return {}


def detect_layout_remote(image_path: str | Path, base_url: str) -> list[dict[str, Any]]:
    """Call Colab POST /layout. Returns list of {type, bbox, order}."""
    out = _post_image(base_url, "/layout", image_path)
    return out.get("regions") or [{"type": "text", "bbox": [0, 0, 1, 1], "order": 0}]


def run_ocr_text_remote(image_path: str | Path, base_url: str) -> list[dict[str, Any]]:
    """Call Colab POST /ocr_text. Returns list of {text, bbox} (same as run_ocr_paddle)."""
    out = _post_image(base_url, "/ocr_text", image_path)
    return out.get("lines") or [{"text": "", "bbox": [0, 0, 0, 0]}]


def run_ocr_math_remote(image_path: str | Path, base_url: str) -> str:
    """Call Colab POST /ocr_math. Returns LaTeX string."""
    out = _post_image(base_url, "/ocr_math", image_path)
    return out.get("latex") or ""


def extract_table_remote(image_path: str | Path, base_url: str) -> list[list[str]]:
    """Call Colab POST /table. Returns 2D list of cell texts."""
    out = _post_image(base_url, "/table", image_path)
    return out.get("cells") or []


def describe_figure_remote(image_path: str | Path, base_url: str) -> str:
    """Call Colab POST /figure. Returns description string."""
    out = _post_image(base_url, "/figure", image_path)
    return out.get("description") or ""
