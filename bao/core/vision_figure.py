"""
Vision for figures/graphs: image → text description.
Stub: optional API (GPT-4V/Claude) or small local model (BLIP, Qwen2-VL-2B) later.
"""

from __future__ import annotations

from pathlib import Path


def describe_figure(image_path: str | Path, *, api_key: str | None = None) -> str:
    """
    Describe figure/graph for AI consumption. Stub: returns empty.
    Later: call vision API or load small vision model (e.g. BLIP-2) when VRAM allows.
    """
    return ""
