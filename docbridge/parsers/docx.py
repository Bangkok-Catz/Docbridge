"""DOCX parser. Walks the body in document order so tables stay in place."""
from __future__ import annotations

import io

from ..models import Block, Document


def parse_docx(data: bytes, filename: str | None = None) -> Document:
    from docx import Document as DocxDocument
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    d = DocxDocument(io.BytesIO(data))
    doc = Document(filename=filename, kind="docx")
    core = d.core_properties
    doc.metadata = {k: v for k, v in {"title": core.title, "author": core.author}.items() if v}

    for child in d.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            p = Paragraph(child, d)
            text = p.text.strip()
            if not text:
                continue
            style = (p.style.name or "") if p.style is not None else ""
            low = style.lower()
            if low == "title":
                doc.blocks.append(Block("heading", text, level=1))
            elif low.startswith("heading"):
                digits = "".join(c for c in low if c.isdigit())
                level = int(digits) if digits else 1
                doc.blocks.append(Block("heading", text, level=min(level, 6)))
            elif "list" in low:
                doc.blocks.append(Block("list_item", text))
            else:
                doc.blocks.append(Block("paragraph", text))
        elif tag == "tbl":
            t = Table(child, d)
            rows = [[c.text.strip() for c in r.cells] for r in t.rows]
            if rows:
                doc.blocks.append(Block("table", rows=rows))
    return doc
