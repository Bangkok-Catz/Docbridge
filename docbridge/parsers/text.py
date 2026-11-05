"""Plain text and Markdown. Handles legacy Thai encodings."""
from __future__ import annotations

import re

from ..models import Block, Document

_HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+(.*\S)\s*$")


def decode_text(data: bytes, warnings: list[str]) -> str:
    for enc in ("utf-8-sig", "utf-8"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            pass
    # cp874 (Windows Thai) is common in older Thai documents and exports
    try:
        text = data.decode("cp874")
        warnings.append("decoded as cp874 (legacy Thai encoding)")
        return text
    except UnicodeDecodeError:
        warnings.append("decoded as latin-1 with replacement")
        return data.decode("latin-1", errors="replace")


def parse_text(data: bytes, filename: str | None = None) -> Document:
    doc = Document(filename=filename, kind="text")
    text = decode_text(data, doc.warnings).replace("\r\n", "\n").replace("\r", "\n")
    for para in re.split(r"\n\s*\n", text):
        lines = [ln for ln in para.split("\n") if ln.strip()]
        if not lines:
            continue
        if len(lines) == 1 and (m := _HEADING.match(lines[0])):
            doc.blocks.append(Block("heading", m.group(2), level=len(m.group(1))))
        elif all(_BULLET.match(ln) for ln in lines):
            doc.blocks.extend(Block("list_item", _BULLET.match(ln).group(1)) for ln in lines)
        else:
            doc.blocks.append(Block("paragraph", "\n".join(ln.strip() for ln in lines)))
    return doc
