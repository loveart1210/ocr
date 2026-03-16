"""
Setup for Google Colab: cài đặt toàn bộ dependency (apt + pip) + Qwen2.5-7B (LLM reasoning), expose .env qua ngrok.

Chạy một lệnh duy nhất (không cần requirements-colab.txt):
  python -m bao.colab_setup

  - Bước 1: apt poppler-utils; pip install (pipeline + transformers, accelerate, bitsandbytes cho Qwen2.5-7B).
  - Bước 2: Server trả .env tại /env + tunnel ngrok, in ra COLAB_ENV_URL và NGROK_TOKEN.

Chỉ cài đặt: python -m bao.colab_setup --install-only
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# --- Điền token ngrok tại đây (hoặc set biến môi trường NGROK_TOKEN) ---
NGROK_TOKEN: str = ""  # Ví dụ: "2abc..."
# ---

HTTP_PORT = 8765
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

# LLM reasoning: Qwen2.5-7B-Instruct (trích tiêu đề, tóm tắt, cấu trúc bài)
QWEN_MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"

# Gói pip cho Colab: pipeline + layout/OCR/math + Qwen2.5-7B (transformers, accelerate, bitsandbytes)
PIP_PACKAGES = [
    "pydantic>=2.6,<3",
    "PyMuPDF>=1.23,<2",
    "python-dotenv>=1.0,<2",
    "pdf2image>=1.16,<2",
    "opencv-python-headless>=4.8,<5",
    "Pillow>=10,<11",
    "paddlepaddle",
    "paddleocr",
    "pix2tex",
    "pyngrok",
    "transformers>=4.40",
    "accelerate",
    "bitsandbytes",
]


def install_colab_deps() -> None:
    """Chạy apt poppler-utils (nếu được) và pip install toàn bộ PIP_PACKAGES."""
    print("--- Cài đặt dependency (apt + pip) ---")
    try:
        subprocess.run(
            ["apt-get", "update"],
            capture_output=True,
            timeout=60,
        )
        subprocess.run(
            ["apt-get", "install", "-y", "poppler-utils"],
            capture_output=True,
            timeout=120,
        )
        print("  apt: poppler-utils ok.")
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
        print(f"  apt: bỏ qua (chạy thủ công nếu cần: apt-get install -y poppler-utils). {e!r}")

    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-q"] + PIP_PACKAGES,
        timeout=600,
    )
    print("  pip: đã cài", " ".join(PIP_PACKAGES))
    print("--- Xong cài đặt ---\n")


def _get_token() -> str:
    t = (NGROK_TOKEN or os.getenv("NGROK_TOKEN") or "").strip()
    if not t:
        print("NGROK_TOKEN chưa có. Điền vào colab_setup.py (biến NGROK_TOKEN) hoặc set env NGROK_TOKEN.", file=sys.stderr)
        sys.exit(1)
    return t


def _env_content() -> bytes:
    if ENV_PATH.exists():
        return ENV_PATH.read_bytes()
    return b"# No .env found; create one or copy .env.example\n"


def run_server_and_ngrok() -> None:
    import threading
    from http.server import HTTPServer, BaseHTTPRequestHandler

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.rstrip("/") == "/env":
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(_env_content())
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format, *args):
            pass

    server = HTTPServer(("127.0.0.1", HTTP_PORT), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    token = _get_token()
    try:
        from pyngrok import ngrok
        ngrok.set_auth_token(token)
        tunnel = ngrok.connect(HTTP_PORT, bind_tls=True)
        url = tunnel.public_url.rstrip("/") + "/env"
        print("\n--- Copy vào .env (trên Colab) ---")
        print(f"COLAB_ENV_URL={url}")
        print(f"NGROK_TOKEN={token}")
        print("---")
        print("\nServer đang chạy. Nhấn Ctrl+C để dừng.")
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    except ImportError:
        print("Cài pyngrok: pip install pyngrok", file=sys.stderr)
        print("Hoặc chạy ngrok thủ công: ngrok http " + str(HTTP_PORT), file=sys.stderr)
        print("Sau đó dùng URL ngrok + /env làm COLAB_ENV_URL.", file=sys.stderr)
        print("\nServer local đang chạy tại http://127.0.0.1:" + str(HTTP_PORT) + "/env")
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    if "--install-only" in sys.argv:
        install_colab_deps()
        sys.exit(0)
    install_colab_deps()
    run_server_and_ngrok()
