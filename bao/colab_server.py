"""
Run on Google Colab: load models (PaddleOCR, pix2tex), expose HTTP API, then ngrok.
Prints BAO_COLAB_URL for you to copy into .env so main.py (local) can call this API.

Usage on Colab:
  !pip install -q pyngrok  # if not already
  !python -m bao.colab_server

Then copy the printed BAO_COLAB_URL into your local .env.
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
from contextlib import contextmanager
from http.server import HTTPServer, BaseHTTPRequestHandler

# Load env from URL if running on Colab (optional)
try:
    from bao.core.env import load_env
    load_env()
except Exception:
    pass

HTTP_PORT = 8766
ENDPOINTS = ("/layout", "/ocr_text", "/ocr_math", "/table", "/figure")


def _load_models():
    """Load PaddleOCR and LatexOCR once."""
    ocr = None
    latex_model = None
    try:
        from paddleocr import PaddleOCR
        use_gpu = os.getenv("USE_GPU", "").strip().lower() in ("1", "true", "yes", "on")
        ocr = PaddleOCR(use_angle_cls=True, lang="vi", use_gpu=use_gpu, show_log=False)
    except ImportError:
        pass
    try:
        from pix2tex.cli import LatexOCR
        latex_model = LatexOCR(arguments=None)
    except Exception:
        pass
    return ocr, latex_model


def _run_layout(ocr, image_bytes: bytes) -> list:
    from PIL import Image
    import numpy as np
    if ocr is None:
        return [{"type": "text", "bbox": [0, 0, 1, 1], "order": 0}]
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    arr = np.array(img)
    result = ocr.ocr(arr, cls=True)
    if not result or not result[0]:
        return [{"type": "text", "bbox": [0, 0, 1, 1], "order": 0}]
    blocks = []
    for i, line in enumerate(result[0]):
        if not line or len(line) < 2:
            continue
        box = line[0]
        if len(box) >= 4:
            bbox = [min(p[0] for p in box), min(p[1] for p in box), max(p[0] for p in box), max(p[1] for p in box)]
        else:
            bbox = [0, 0, 1, 1]
        blocks.append({"type": "text", "bbox": bbox, "order": i})
    return blocks if blocks else [{"type": "text", "bbox": [0, 0, 1, 1], "order": 0}]


def _run_ocr_text(ocr, image_bytes: bytes) -> list:
    if ocr is None:
        return [{"text": "", "bbox": [0, 0, 0, 0]}]
    with temp_file(image_bytes) as path:
        result = ocr.ocr(str(path), cls=True)
    if not result or not result[0]:
        return [{"text": "", "bbox": [0, 0, 0, 0]}]
    out = []
    for line in result[0]:
        if not line or len(line) < 2:
            continue
        box, (text, _) = line[0], line[1]
        bbox = [min(p[0] for p in box), min(p[1] for p in box), max(p[0] for p in box), max(p[1] for p in box)] if len(box) >= 4 else [0, 0, 0, 0]
        out.append({"text": text or "", "bbox": bbox})
    return out if out else [{"text": "", "bbox": [0, 0, 0, 0]}]


def _run_ocr_math(latex_model, image_bytes: bytes) -> str:
    if latex_model is None:
        return ""
    with temp_file(image_bytes) as path:
        return latex_model(str(path)) or ""


def _run_table(ocr, image_bytes: bytes) -> list:
    if ocr is None:
        return []
    with temp_file(image_bytes) as path:
        result = ocr.ocr(str(path), cls=True)
    if not result or not result[0]:
        return []
    return [[line[1][0] if line and len(line) >= 2 and isinstance(line[1], (list, tuple)) else str(line[1])] for line in result[0] if line and len(line) >= 2]


@contextmanager
def temp_file(data: bytes):
    fd, path = tempfile.mkstemp(suffix=".png")
    try:
        os.write(fd, data)
        os.close(fd)
        yield path
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path not in ENDPOINTS:
            self.send_response(404)
            self.end_headers()
            return
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" in content_type:
            # Parse boundary and extract image
            boundary = content_type.split("boundary=")[-1].strip().strip('"')
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            image_bytes = _extract_multipart_image(body, boundary)
        else:
            image_bytes = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if not image_bytes:
            self._send_json(400, {"error": "no image"})
            return
        ocr, latex = self.server.ocr, self.server.latex_model
        try:
            if self.path == "/layout":
                out = _run_layout(ocr, image_bytes)
                self._send_json(200, {"regions": out})
            elif self.path == "/ocr_text":
                out = _run_ocr_text(ocr, image_bytes)
                self._send_json(200, {"lines": out})
            elif self.path == "/ocr_math":
                out = _run_ocr_math(latex, image_bytes)
                self._send_json(200, {"latex": out})
            elif self.path == "/table":
                out = _run_table(ocr, image_bytes)
                self._send_json(200, {"cells": out})
            elif self.path == "/figure":
                self._send_json(200, {"description": ""})
            else:
                self.send_response(404)
                self.end_headers()
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def _send_json(self, code: int, obj: dict):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"BAO Colab API: POST /layout, /ocr_text, /ocr_math, /table, /figure with image body or multipart.")
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        pass


def _extract_multipart_image(body: bytes, boundary: bytes | str) -> bytes:
    if isinstance(boundary, str):
        boundary = boundary.encode("utf-8")
    if not boundary.startswith(b"--"):
        boundary = b"--" + boundary
    parts = body.split(boundary)
    for part in parts:
        if b"Content-Disposition" not in part or b"image" not in part.lower():
            continue
        if b"\r\n\r\n" in part:
            payload = part.split(b"\r\n\r\n", 1)[1]
        elif b"\n\n" in part:
            payload = part.split(b"\n\n", 1)[1]
        else:
            continue
        if payload.endswith(b"\r\n"):
            payload = payload[:-2]
        elif payload.endswith(b"\n"):
            payload = payload[:-1]
        if payload:
            return payload
    return b""


def run():
    ocr, latex = _load_models()
    server = HTTPServer(("0.0.0.0", HTTP_PORT), Handler)
    server.ocr = ocr
    server.latex_model = latex
    print("Models loaded. Starting HTTP server on port", HTTP_PORT, "...")
    try:
        from pyngrok import ngrok
        token = os.getenv("NGROK_TOKEN", "").strip()
        if token:
            ngrok.set_auth_token(token)
        tunnel = ngrok.connect(HTTP_PORT, bind_tls=True)
        base = tunnel.public_url.rstrip("/")
        print("\n--- Copy into your local .env (main.py will use this URL) ---")
        print(f"BAO_COLAB_URL={base}")
        print("---")
    except ImportError:
        base = f"http://localhost:{HTTP_PORT}"
        print("pyngrok not installed. Install with: pip install pyngrok")
        print("Then set NGROK_TOKEN and run again to get a public URL.")
        print("Local only: BAO_COLAB_URL=" + base)
    print("\nServer running. Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    run()
