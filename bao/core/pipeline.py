"""
PDF or image folder → JSON pipeline. Output schema: { chapter: { title, description, lessons: [{ lessonTitle, type, summary, file }] } }.

Flow: For each page image → layout detection (detect_layout_paddle) → list of regions (bbox, type).
Per region: text/title → ocr_text; formula → ocr_math (LaTeX); table → extract_table + table_to_markdown; figure → vision_figure.
Merge region outputs in order into page markdown. Build chapter with one lesson per page (or placeholder on failure).
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from bao.core.config import DEFAULT_DPI, LESSONS_SUBDIR, OUTPUT_JSON_NAME, PAGES_SUBDIR
from bao.core.pdf import pdf_to_page_images
from bao.core.schema import Chapter, Lesson, PdfToJsonRoot, validate_pdf_to_json

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def _get_use_gpu() -> bool:
    """Read USE_GPU from env (1/true/yes/on)."""
    v = os.getenv("USE_GPU", "").strip().lower()
    return v in ("1", "true", "yes", "on")


def _get_vision_api_key() -> str | None:
    """Read vision API key from OPENAI_API_KEY or VISION_API_KEY."""
    return os.getenv("OPENAI_API_KEY") or os.getenv("VISION_API_KEY") or None


def _bbox_to_crop_box(bbox: list[float], width: int, height: int) -> tuple[int, int, int, int]:
    """Convert bbox [x0,y0,x1,y1] (pixels or normalized 0..1) to (left, upper, right, lower) ints."""
    x0, y0, x1, y1 = bbox[0], bbox[1], bbox[2], bbox[3]
    if max(bbox) <= 1.0 and min(bbox) >= 0:
        x0, x1 = x0 * width, x1 * width
        y0, y1 = y0 * height, y1 * height
    left = max(0, min(int(x0), width - 1))
    upper = max(0, min(int(y0), height - 1))
    right = max(left + 1, min(int(x1), width))
    lower = max(upper + 1, min(int(y1), height))
    return (left, upper, right, lower)


def _crop_region_to_temp(
    image_path: str | Path,
    bbox: list[float],
    width: int,
    height: int,
    temp_dir: Path,
) -> Path | None:
    """Crop image region to a temporary file. Caller should unlink when done."""
    from bao.core import images as img_mod

    box = _bbox_to_crop_box(bbox, width, height)
    if box[2] <= box[0] or box[3] <= box[1]:
        return None
    try:
        cropped = img_mod.image_crop(image_path, box)
    except Exception:
        return None
    fd, path = tempfile.mkstemp(suffix=".png", dir=str(temp_dir))
    try:
        os.write(fd, cropped)
        return Path(path)
    finally:
        os.close(fd)


def _process_region(
    region: dict[str, Any],
    page_path: str | Path,
    width: int,
    height: int,
    use_gpu: bool,
    vision_api_key: str | None,
    temp_dir: Path,
    colab_base_url: str | None = None,
) -> str:
    """Run the appropriate module for region type; return markdown fragment. Use Colab API if colab_base_url set."""
    rtype = (region.get("type") or "text").lower()
    bbox = region.get("bbox") or [0, 0, 1, 1]
    if len(bbox) < 4:
        bbox = [0, 0, 1, 1]

    crop_path = _crop_region_to_temp(page_path, bbox, width, height, temp_dir)
    if crop_path is None:
        return ""

    try:
        if colab_base_url:
            from bao.core import colab_client as remote
            if rtype in ("formula", "math"):
                latex = remote.run_ocr_math_remote(crop_path, colab_base_url)
                if latex:
                    return f"\n$${latex}$$\n"
                return ""
            if rtype == "table":
                cells = remote.extract_table_remote(crop_path, colab_base_url)
                if cells:
                    from bao.core import table as table_mod
                    return "\n" + table_mod.table_to_markdown(cells) + "\n"
                return ""
            if rtype in ("figure", "picture", "image"):
                desc = remote.describe_figure_remote(crop_path, colab_base_url)
                if desc:
                    return f"\n*Hình: {desc}*\n"
                return ""
            ocr_result = remote.run_ocr_text_remote(crop_path, colab_base_url)
            from bao.core import ocr_text
            return ocr_text.extract_text_from_ocr_result(ocr_result)
        from bao.core import ocr_math
        from bao.core import ocr_text
        from bao.core import table as table_mod
        from bao.core import vision_figure
        if rtype in ("formula", "math"):
            latex = ocr_math.run_math_ocr_pix2tex(crop_path)
            if latex:
                return f"\n$${latex}$$\n"
            return ""
        if rtype == "table":
            cells = table_mod.extract_table_paddle(crop_path)
            if cells:
                return "\n" + table_mod.table_to_markdown(cells) + "\n"
            return ""
        if rtype in ("figure", "picture", "image"):
            desc = vision_figure.describe_figure(crop_path, api_key=vision_api_key)
            if desc:
                return f"\n*Hình: {desc}*\n"
            return ""
        ocr_result = ocr_text.run_ocr_paddle(crop_path, lang="vi", use_gpu=use_gpu)
        return ocr_text.extract_text_from_ocr_result(ocr_result)
    except Exception:
        return ""
    finally:
        try:
            crop_path.unlink(missing_ok=True)
        except OSError:
            pass


def _process_page(
    page_path: str | Path,
    use_gpu: bool,
    vision_api_key: str | None,
    colab_base_url: str | None = None,
) -> str | None:
    """
    Run layout on page, then per-region OCR/table/figure; merge into one markdown string.
    If colab_base_url set, use Colab API for layout and all regions.
    Returns None on critical failure (e.g. layout raises).
    """
    from PIL import Image

    page_path = Path(page_path)
    if not page_path.is_file():
        return None
    try:
        img = Image.open(page_path).convert("RGB")
        width, height = img.size
    except Exception:
        return None
    try:
        if colab_base_url:
            from bao.core import colab_client as remote
            regions = remote.detect_layout_remote(page_path, colab_base_url)
        else:
            from bao.core import layout as layout_mod
            regions = layout_mod.detect_layout_paddle(page_path)
    except Exception:
        return None
    if not regions:
        return None

    # Sort by vertical then horizontal position
    def order_key(r: dict[str, Any]) -> tuple[float, float]:
        b = r.get("bbox") or [0, 0, 1, 1]
        return (b[1], b[0]) if len(b) >= 4 else (0, 0)

    regions = sorted(regions, key=order_key)

    temp_dir = Path(tempfile.mkdtemp(prefix="bao_pipeline_"))
    parts: list[str] = []
    try:
        for region in regions:
            part = _process_region(
                region,
                page_path,
                width,
                height,
                use_gpu,
                vision_api_key,
                temp_dir,
                colab_base_url=colab_base_url,
            )
            if part:
                parts.append(part.strip())
    finally:
        try:
            for p in temp_dir.iterdir():
                p.unlink(missing_ok=True)
            temp_dir.rmdir()
        except OSError:
            pass

    if not parts:
        return None
    return "\n\n".join(parts)


def _build_root_from_page_contents(
    page_paths: list[str],
    page_contents: list[str],
) -> PdfToJsonRoot:
    """Build one chapter with one lesson per page; lesson file = lessons/bai-{i+1}.md."""
    lessons: list[Lesson] = []
    for i, content in enumerate(page_contents):
        title = f"Bài {i + 1}"
        summary = (content.split("\n")[0][:200].strip() if content else "Nội dung trang.") or "Nội dung trang."
        lessons.append(
            Lesson(
                lessonTitle=title,
                type="reading",
                summary=summary,
                file=f"{LESSONS_SUBDIR}/bai-{i + 1}.md",
            )
        )
    return PdfToJsonRoot(chapter=Chapter(
        title="Chương 1",
        description="Nội dung từ layout và OCR.",
        lessons=lessons,
    ))


def list_page_images(images_dir: str | Path) -> list[str]:
    """List image paths in directory, sorted (page-0001.png, page-0002.png, then *.png, *.jpg)."""
    d = Path(images_dir)
    if not d.is_dir():
        return []
    paths: list[str] = []
    for ext in IMAGE_EXTENSIONS:
        paths.extend(str(p) for p in d.glob(f"*{ext}"))
    paths.sort(key=lambda p: (Path(p).stem.replace("page-", "").zfill(8), p))
    return paths


def _build_placeholder_root(num_lessons: int = 1) -> PdfToJsonRoot:
    lessons = [
        Lesson(
            lessonTitle="Bài 1 (placeholder)",
            type="reading",
            summary="Tóm tắt bài học (placeholder).",
            file=f"{LESSONS_SUBDIR}/bai-1.md",
        )
    ]
    if num_lessons > 1:
        lessons = [
            Lesson(lessonTitle=f"Bài {i + 1} (placeholder)", type="reading", summary="Tóm tắt.", file=f"{LESSONS_SUBDIR}/bai-{i + 1}.md")
            for i in range(num_lessons)
        ]
    return PdfToJsonRoot(chapter=Chapter(
        title="Chương 1",
        description="Placeholder (layout/OCR chưa nối).",
        lessons=lessons,
    ))


def run_pipeline_from_images(
    page_image_paths: list[str],
    output_dir: str | Path,
    *,
    write_md: bool = True,
) -> dict[str, Any]:
    """
    Run pipeline from existing page images: layout → per-region OCR/table/figure → chapter + lessons.
    On layout/OCR failure or optional deps missing, falls back to placeholder root and placeholder md.
    Writes JSON + optional .md to output_dir. Return shape: json_path, md_paths, root, page_paths.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    num_pages = len(page_image_paths)
    use_gpu = _get_use_gpu()
    vision_api_key = _get_vision_api_key()
    try:
        from bao.core.colab_client import get_colab_url
        colab_base_url = get_colab_url()
    except Exception:
        colab_base_url = None

    page_contents: list[str] | None = None
    try:
        page_contents = []
        for p in page_image_paths:
            content = _process_page(p, use_gpu, vision_api_key, colab_base_url=colab_base_url)
            page_contents.append(content if content else "")
        has_real = any(s and s.strip() for s in page_contents)
        if not has_real or not page_contents:
            page_contents = None
    except Exception:
        page_contents = None

    if page_contents is None or num_pages == 0:
        root = _build_placeholder_root(num_lessons=max(1, min(num_pages, 10)))
    else:
        root = _build_root_from_page_contents(page_image_paths, page_contents)

    obj = root.model_dump(mode="json", exclude_none=True)
    validate_pdf_to_json(obj)
    json_path = output_dir / OUTPUT_JSON_NAME
    json_path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_paths: list[Path] = []
    if write_md and root.chapter.lessons:
        (output_dir / LESSONS_SUBDIR).mkdir(parents=True, exist_ok=True)
        for i, les in enumerate(root.chapter.lessons):
            p = output_dir / LESSONS_SUBDIR / (Path(les.file).name or f"bai-{i + 1}.md")
            if page_contents is not None and i < len(page_contents) and page_contents[i]:
                body = page_contents[i]
            else:
                body = les.summary
            p.write_text(f"# {les.lessonTitle}\n\n{body}\n", encoding="utf-8")
            md_paths.append(p)
    return {"page_paths": page_image_paths, "root": root, "json_path": json_path, "md_paths": md_paths}


def run_pipeline(
    pdf_path: str | Path,
    output_dir: str | Path,
    *,
    dpi: int = DEFAULT_DPI,
    write_md: bool = True,
) -> dict[str, Any]:
    """Run pipeline from PDF: extract pages then same as run_pipeline_from_images."""
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    if not pdf_path.exists() or not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    pages_dir = output_dir / PAGES_SUBDIR
    pages_dir.mkdir(parents=True, exist_ok=True)
    page_paths = pdf_to_page_images(pdf_path, output_dir=pages_dir, dpi=dpi)
    return run_pipeline_from_images(page_paths, output_dir, write_md=write_md)
