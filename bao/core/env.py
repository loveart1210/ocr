"""Load .env and optionally fetch env from COLAB_ENV_URL (e.g. ngrok)."""

from __future__ import annotations

import os
import sys


def load_env() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    url = os.getenv("COLAB_ENV_URL", "").strip()
    if not url:
        return
    token = os.getenv("NGROK_TOKEN", "").strip()
    try:
        import urllib.request
        req = urllib.request.Request(url)
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode("utf-8", errors="replace")
        for line in body.splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip().strip('"').strip("'")
    except Exception as e:
        print(f"Warning: COLAB_ENV_URL: {e}", file=sys.stderr)
