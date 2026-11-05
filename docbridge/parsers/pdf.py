"""PDF parser built on pdfplumber.

Per page: tables are extracted separately, remaining text is grouped into
lines, headings are detected from font size, and lines are merged into
paragraphs. Pages with no text layer fall back to OCR when available.
"""
from __future__ import annotations

import io
import statistics

from ..detect import is_thai_char
from ..models import Block, Document
from .ocr import ocr_available, ocr_image


def _join(a: str, b: str) -> str:
    """Join two lines. Thai has no inter-word spaces, so no space is added."""
    if not a:
        return b
    if is_thai_char(a[-1]) and is_thai_char(b[:1]):
        return a + b
    if a.endswith("-") and b[:1].islower():  # English hyphenation
        return a[:-1] + b
    return a + " " + b


def _page_blocks(page, page_no: int) -> list[Block]:
    blocks: list[Block] = []
    tables = page.find_tables()
    body = page
    for t in tables:
        body = body.outside_bbox(t.bbox)

    lines = body.extract_text_lines(return_chars=True, layout=False, strip=True)
    sizes = [round(c["size"], 1) for ln in lines for c in ln["chars"] if c.get("size")]
    body_size = statistics.median(sizes) if sizes else 0

    items: list[tuple[float, Block]] = []  # (top, block)
    para = ""
    para_top = 0.0
    last_bottom = None
    last_size = body_size

    def flush():
        nonlocal para
        if para.strip():
            items.append((para_top, Block("paragraph", para.strip(), page=page_no)))
        para = ""

    for ln in lines:
        text = ln["text"].strip()
        if not text:
            continue
        csizes = [c["size"] for c in ln["chars"] if c.get("size")]
        size = statistics.median(csizes) if csizes else body_size
        is_heading = body_size and size >= body_size * 1.25 and len(text) < 120
        if is_heading:
            flush()
            ratio = size / body_size
            level = 1 if ratio >= 1.8 else 2 if ratio >= 1.45 else 3
            items.append((ln["top"], Block("heading", text, level=level, page=page_no)))
            last_bottom = None
            continue
        if text[:1] in "•-–*" and len(text) > 2 and text[1] == " ":
            flush()
            items.append((ln["top"], Block("list_item", text[2:].strip(), page=page_no)))
            last_bottom = None
            continue
        gap = (ln["top"] - last_bottom) if last_bottom is not None else 0
        if para and gap > 0.6 * (last_size or size):
            flush()
        if not para:
            para_top = ln["top"]
        para = _join(para, text)
        last_bottom, last_size = ln["bottom"], size
    flush()

    for t in tables:
        rows = [[(c or "").replace("\n", " ").strip() for c in r] for r in t.extract()]
        rows = [r for r in rows if any(r)]
        if rows:
            items.append((t.bbox[1], Block("table", rows=rows, page=page_no)))

    items.sort(key=lambda x: x[0])
    blocks.extend(b for _, b in items)
    return blocks


def parse_pdf(data: bytes, filename: str | None = None, *, ocr: bool = True) -> Document:
    import pdfplumber

    doc = Document(filename=filename, kind="pdf")
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        doc.pages = len(pdf.pages)
        info = pdf.metadata or {}
        doc.metadata = {k.lower(): v for k, v in info.items() if k in ("Title", "Author") and v}
        for i, page in enumerate(pdf.pages, start=1):
            blocks = _page_blocks(page, i)
            if not blocks and not page.chars:
                if ocr and ocr_available():
                    img = page.to_image(resolution=200).original
                    text, lang = ocr_image(img)
                    for p in [p.strip() for p in text.split("\n\n") if p.strip()]:
                        blocks.append(Block("paragraph", p, page=i))
                    doc.warnings.append(f"page {i}: no text layer, used OCR ({lang})")
                else:
                    doc.warnings.append(f"page {i}: no text layer (scanned?) and OCR is unavailable")
            doc.blocks.extend(blocks)
    return doc
