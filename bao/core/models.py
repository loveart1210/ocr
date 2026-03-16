"""Load models for Colab (VRAM limit, toggles from config)."""

from __future__ import annotations

import subprocess
import sys
from typing import Any

from bao.core.config import ENABLE_PADDLE_OCR, ENABLE_PIX2TEX, VRAM_LIMIT_GB


def _pip(packages: list[str]) -> None:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q"] + packages)


def get_device_and_memory_info() -> dict[str, Any]:
    out: dict[str, Any] = {"gpu_available": False, "device_name": None, "vram_total_mb": None, "vram_used_mb": None}
    try:
        import torch
        if torch.cuda.is_available():
            out["gpu_available"] = True
            out["device_name"] = torch.cuda.get_device_name(0)
            out["vram_total_mb"] = torch.cuda.get_device_properties(0).total_memory // (1024 * 1024)
            out["vram_used_mb"] = torch.cuda.memory_allocated(0) // (1024 * 1024)
    except Exception:
        pass
    if out["vram_total_mb"] is None:
        try:
            r = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.used", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5,
            )
            if r.returncode == 0 and r.stdout.strip():
                parts = r.stdout.strip().split(",")
                if len(parts) >= 3:
                    out["device_name"] = parts[0].strip()
                    out["vram_total_mb"] = int(parts[1].strip().split()[0])
                    out["vram_used_mb"] = int(parts[2].strip().split()[0])
                    out["gpu_available"] = True
        except Exception:
            pass
    return out


def load_models_for_colab(
    vram_limit_gb: int | None = None,
    enable_paddle_ocr: bool | None = None,
    enable_pix2tex: bool | None = None,
) -> dict[str, Any]:
    vram_limit_gb = vram_limit_gb if vram_limit_gb is not None else VRAM_LIMIT_GB
    enable_paddle = enable_paddle_ocr if enable_paddle_ocr is not None else ENABLE_PADDLE_OCR
    enable_pix = enable_pix2tex if enable_pix2tex is not None else ENABLE_PIX2TEX
    vram_mb = vram_limit_gb * 1024
    status: dict[str, Any] = {
        "vram_limit_mb": vram_mb,
        "device_info": get_device_and_memory_info(),
        "installed": [],
        "loaded": {},
        "vram_used_mb": 0,
    }
    _pip(["pydantic>=2.6", "PyMuPDF>=1.23"])
    status["installed"].extend(["pydantic", "PyMuPDF"])
    if enable_paddle:
        try:
            _pip(["paddlepaddle", "paddleocr"])
            status["loaded"]["paddleocr"] = {"device": "cpu", "vram_mb": 0}
        except Exception as e:
            status["loaded"]["paddleocr"] = {"error": str(e)}
    else:
        status["loaded"]["paddleocr"] = {"skipped": True}
    try:
        _pip(["pytesseract"])
        status["loaded"]["pytesseract"] = {"device": "cpu", "vram_mb": 0}
    except Exception as e:
        status["loaded"]["pytesseract"] = {"error": str(e)}
    if enable_pix:
        try:
            import torch
            info = status["device_info"]
            if info.get("gpu_available") and torch.cuda.is_available() and (info.get("vram_used_mb") or 0) + 6000 <= vram_mb:
                _pip(["pix2tex"])
                from pix2tex.cli import LatexOCR
                _ = LatexOCR(arguments=None)
                status["loaded"]["pix2tex"] = {"device": "cuda", "vram_mb": 6000}
                status["vram_used_mb"] = 6000
            else:
                status["loaded"]["pix2tex"] = {"device": "cpu", "vram_mb": 0, "note": "GPU limit or no GPU"}
        except Exception as e:
            status["loaded"]["pix2tex"] = {"error": str(e)}
    else:
        status["loaded"]["pix2tex"] = {"skipped": True}
    info = status.get("device_info", {})
    print("--- Device & VRAM ---")
    print(f"  GPU: {info.get('gpu_available')}, Device: {info.get('device_name')}, VRAM: {info.get('vram_used_mb')}/{info.get('vram_total_mb')} MB, limit: {vram_mb} MB")
    print("--- Loaded ---")
    for name, m in status.get("loaded", {}).items():
        print(f"  {name}: {m}")
    return status
