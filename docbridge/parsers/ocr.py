"""OCR for page images: LFM3-VL-2B (if configured) or Tesseract.

engine:
  auto       LFM3-VL when DOCBRIDGE_VLM is set, else Tesseract
  vlm        LFM3-VL only (warns if not configured)
  tesseract  Tesseract only
"""
from __future__ import annotations

import io
import shutil

from ..models import Block, Document

ENGINES = ("auto", "vlm", "tesseract")


def tesseract_available() -> bool:
    try:
        import pytesseract  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError:
        return False
    return shutil.which("tesseract") is not None


def ocr_available(engine: str = "auto") -> bool:
    from ..vlm import get_backend

    if engine in ("auto", "vlm") and get_backend() is not None:
        return True
    return tesseract_available()  # "vlm" without a backend falls back to Tesseract, with a warning


def _tesseract_lang() -> str:
    import pytesseract

    have = set(pytesseract.get_languages(config=""))
    return "+".join(l for l in ("tha", "eng") if l in have) or "eng"


def ocr_to_blocks(img, page: int | None, engine: str, warnings: list[str]) -> tuple[list[Block], str | None]:
    """OCR one image. Returns (blocks, engine name used or None)."""
    from ..vlm import get_backend
    from .text import markdown_to_blocks

    if engine not in ENGINES:
        raise ValueError(f"unknown OCR engine {engine!r}; use one of {ENGINES}")

    backend = get_backend() if engine in ("auto", "vlm") else None
    if backend is not None:
        try:
            md = backend.page_to_markdown(img)
            return markdown_to_blocks(md, page=page), backend.name
        except Exception as exc:  # server down, OOM, etc.
            warnings.append(f"{backend.name} failed ({exc.__class__.__name__}: {exc}); falling back to Tesseract")
    elif engine == "vlm":
        warnings.append("OCR engine 'vlm' requested but DOCBRIDGE_VLM is not configured; falling back to Tesseract")

    if not tesseract_available():
        return [], None
    import pytesseract

    lang = _tesseract_lang()
    if "tha" not in lang:
        warnings.append("tesseract 'tha' language pack not installed; Thai text will be unreliable")
    text = pytesseract.image_to_string(img, lang=lang)
    blocks = [Block("paragraph", p.strip(), page=page) for p in text.split("\n\n") if p.strip()]
    return blocks, f"tesseract ({lang})"


def parse_image(data: bytes, filename: str | None = None, *, engine: str = "auto") -> Document:
    doc = Document(filename=filename, kind="image", pages=1)
    if not ocr_available(engine):
        doc.warnings.append(
            "OCR unavailable: set DOCBRIDGE_VLM to use LFM3-VL-2B, or install the 'ocr' extra and tesseract-ocr-tha"
        )
        return doc
    from PIL import Image

    doc.blocks, used = ocr_to_blocks(Image.open(io.BytesIO(data)), 1, engine, doc.warnings)
    if used:
        doc.metadata["ocr_engine"] = used
    return doc
