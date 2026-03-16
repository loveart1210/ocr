"""Config from env. Call core.env.load_env() before importing this."""

from __future__ import annotations

import os


def _env_int(key: str, default: int) -> int:
    v = os.getenv(key)
    if v is None:
        return default
    try:
        return int(v.strip())
    except ValueError:
        return default


def _env_bool(key: str, default: bool) -> bool:
    v = os.getenv(key)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


DEFAULT_DPI = _env_int("DPI", 200)
VRAM_LIMIT_GB = _env_int("VRAM_LIMIT_GB", 16)
ENABLE_PADDLE_OCR = _env_bool("ENABLE_PADDLE_OCR", True)
ENABLE_PIX2TEX = _env_bool("ENABLE_PIX2TEX", True)
PAGES_SUBDIR = "pages"
LESSONS_SUBDIR = "lessons"
OUTPUT_JSON_NAME = "out.json"
