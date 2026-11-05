"""OCR via Tesseract. Optional: install the `ocr` extra and tesseract-ocr + tesseract-ocr-tha."""
from __future__ import annotations

import io
import shutil

from ..models import Block, Document


def ocr_available() -> bool:
    try:
        import pytesseract  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError:
        return False
    return shutil.which("tesseract") is not None


def _lang() -> str:
    import pytesseract

    have = set(pytesseract.get_languages(config=""))
    wanted = [l for l in ("tha", "eng") if l in have]
    return "+".join(wanted) or "eng"


def ocr_image(img) -> tuple[str, str]:
    """Return (text, languages used) for a PIL image."""
    import pytesseract

    lang = _lang()
    return pytesseract.image_to_string(img, lang=lang), lang


def parse_image(data: bytes, filename: str | None = None) -> Document:
    doc = Document(filename=filename, kind="image")
    if not ocr_available():
        doc.warnings.append("OCR unavailable: install the 'ocr' extra and tesseract-ocr (with the 'tha' language pack)")
        return doc
    from PIL import Image

    text, lang = ocr_image(Image.open(io.BytesIO(data)))
    if "tha" not in lang:
        doc.warnings.append("tesseract 'tha' language pack not installed; Thai text will be unreliable")
    for para in [p.strip() for p in text.split("\n\n") if p.strip()]:
        doc.blocks.append(Block("paragraph", para.replace("\n", " " if "tha" not in lang else "\n"), page=1))
    doc.pages = 1
    return doc
