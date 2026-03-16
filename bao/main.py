"""
Workflow entrypoint: load env, parse CLI, run pipeline / load-models / schema.
  python -m bao.main run <pdf_or_images_dir> [-o output_dir_or_file] [--pipeline] [--no-md]
  - Input: PDF file hoặc thư mục ảnh (raw/.../sgk_toán_tập1).
  - Output: thư mục (ví dụ output/kết nối tri thức/sgk_toán_tập1) chứa out.json + lessons/*.md.
  - JSON schema: { "chapter": { "title", "description", "lessons": [{ "lessonTitle", "type", "summary", "file" }] } }.
  python -m bao.main load-models
  python -m bao.main schema
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from bao.core.env import load_env

load_env()

from bao.core.config import DEFAULT_DPI, VRAM_LIMIT_GB
from bao.core.models import load_models_for_colab
from bao.core.pdf import pdf_to_page_images
from bao.core.pipeline import list_page_images, run_pipeline, run_pipeline_from_images
from bao.core.schema import Chapter, Lesson, PdfToJsonRoot, export_json_schema, validate_pdf_to_json


def _default_output_dir_for_input(input_path: Path) -> Path:
    """Nếu input nằm dưới raw/, output mặc định = output/ + cùng relative path."""
    try:
        parts = input_path.resolve().parts
        if "raw" in parts:
            i = parts.index("raw")
            return Path("output").joinpath(*parts[i + 1 :])
    except Exception:
        pass
    return Path("output") / input_path.name


def _cmd_run(args: argparse.Namespace) -> int:
    path = Path(args.input_path)
    if not path.exists():
        print(f"Error: not found: {path}", file=sys.stderr)
        return 1

    if path.is_dir():
        page_paths = list_page_images(path)
        if not page_paths:
            print(f"Error: no images in directory: {path}", file=sys.stderr)
            return 1
        output_dir = Path(args.output) if args.output else _default_output_dir_for_input(path)
        output_dir = output_dir.parent if output_dir.suffix else output_dir
        r = run_pipeline_from_images(page_paths, output_dir, write_md=not args.no_md)
        if args.output and Path(args.output).suffix:
            shutil.copy(r["json_path"], args.output)
        else:
            sys.stdout.write(r["json_path"].read_text(encoding="utf-8"))
        return 0

    if not path.is_file():
        print(f"Error: not a file or directory: {path}", file=sys.stderr)
        return 1
    if args.pipeline:
        out = Path(args.output).parent if args.output and Path(args.output).suffix else (Path(args.output) if args.output else Path("output"))
        r = run_pipeline(path, out, dpi=args.dpi, write_md=not args.no_md)
        if args.output and Path(args.output).suffix:
            shutil.copy(r["json_path"], args.output)
        else:
            sys.stdout.write(r["json_path"].read_text(encoding="utf-8"))
        return 0
    pdf_to_page_images(path, output_dir=args.pages_dir, dpi=args.dpi)
    root = PdfToJsonRoot(chapter=Chapter(title="Chương 1", description="Placeholder.", lessons=[Lesson(lessonTitle="Bài 1", type="reading", summary="Tóm tắt bài học.", file="lessons/bai-1.md")]))
    txt = json.dumps(root.model_dump(mode="json", exclude_none=True), ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(txt + "\n", encoding="utf-8")
    else:
        sys.stdout.write(txt + "\n")
    return 0


def _cmd_load_models(args: argparse.Namespace) -> int:
    load_models_for_colab(vram_limit_gb=getattr(args, "vram_limit_gb", None) or VRAM_LIMIT_GB)
    return 0


def _cmd_schema(args: argparse.Namespace) -> int:
    sys.stdout.write(json.dumps(export_json_schema(), ensure_ascii=False, indent=2) + "\n")
    return 0


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="bao", description="ocr_sgk/bao: run pipeline, load models, schema.")
    sub = p.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run", help="Run on PDF file hoặc thư mục ảnh (raw/.../sgk_toán_tập1).")
    r.add_argument("input_path", help="Đường dẫn PDF hoặc thư mục ảnh.")
    r.add_argument("-o", "--output", help="Thư mục output (vd: output/kết nối tri thức/sgk_toán_tập1) hoặc file .json.")
    r.add_argument("--pages-dir")
    r.add_argument("--dpi", type=int, default=DEFAULT_DPI)
    r.add_argument("--pipeline", action="store_true")
    r.add_argument("--no-md", action="store_true")
    lm = sub.add_parser("load-models", help="Install and load models (Colab).")
    lm.add_argument("--vram-limit-gb", type=int, default=None)
    sub.add_parser("schema", help="Print JSON Schema.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv or sys.argv[1:])
    if args.command == "run":
        return _cmd_run(args)
    if args.command == "load-models":
        return _cmd_load_models(args)
    if args.command == "schema":
        return _cmd_schema(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
