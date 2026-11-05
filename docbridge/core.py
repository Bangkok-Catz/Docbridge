"""Public entry points."""
from __future__ import annotations

from pathlib import Path

from .detect import detect_language, sniff_kind
from .models import Document
from .thai import normalize_thai


def parse_bytes(
    data: bytes,
    filename: str | None = None,
    *,
    ocr: bool = True,
    normalize: bool = True,
    thai_digits: bool = False,
    ocr_engine: str = "auto",
) -> Document:
    """Parse a document from bytes. The file kind is sniffed, not trusted from the name.

    ocr_engine: "auto" (LFM3-VL-2B if DOCBRIDGE_VLM is set, else Tesseract), "vlm" or "tesseract".
    """
    from .parsers.ocr import ENGINES

    if ocr_engine not in ENGINES:
        raise ValueError(f"ocr_engine must be one of {ENGINES}")
    kind = sniff_kind(data, filename)
    if kind == "pdf":
        from .parsers.pdf import parse_pdf

        doc = parse_pdf(data, filename, ocr=ocr, engine=ocr_engine)
    elif kind == "docx":
        from .parsers.docx import parse_docx

        doc = parse_docx(data, filename)
    elif kind == "html":
        from .parsers.html import parse_html

        doc = parse_html(data, filename)
    elif kind == "image":
        from .parsers.ocr import parse_image

        doc = parse_image(data, filename, engine=ocr_engine) if ocr else Document(filename=filename, kind="image", warnings=["OCR disabled"])
    else:
        from .parsers.text import parse_text

        doc = parse_text(data, filename)

    if normalize:
        for b in doc.blocks:
            b.text = normalize_thai(b.text, thai_digits=thai_digits)
            b.rows = [[normalize_thai(c, thai_digits=thai_digits) for c in r] for r in b.rows]

    doc.language, doc.language_ratio = detect_language(doc.text)
    return doc


def parse_file(path: str | Path, **kwargs) -> Document:
    p = Path(path)
    return parse_bytes(p.read_bytes(), p.name, **kwargs)
