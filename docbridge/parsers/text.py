"""Plain text and Markdown. Handles legacy Thai encodings and pipe tables."""
from __future__ import annotations

import re

from ..models import Block, Document

_HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+(.*\S)\s*$")
_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")


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


def _row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", s)]


def _is_table(lines: list[str]) -> bool:
    return len(lines) >= 2 and "|" in lines[0] and bool(_TABLE_SEP.match(lines[1]))


def markdown_to_blocks(text: str, page: int | None = None) -> list[Block]:
    """Parse Markdown-ish text (also what the VLM returns) into blocks."""
    blocks: list[Block] = []
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    for para in re.split(r"\n\s*\n", text):
        lines = [ln for ln in para.split("\n") if ln.strip()]
        while lines:
            first = lines[0]
            if m := _HEADING.match(first):
                blocks.append(Block("heading", m.group(2), level=len(m.group(1)), page=page))
                lines = lines[1:]
            elif _is_table(lines):
                n = 2
                while n < len(lines) and "|" in lines[n]:
                    n += 1
                rows = [_row(lines[0])] + [_row(ln) for ln in lines[2:n]]
                blocks.append(Block("table", rows=rows, page=page))
                lines = lines[n:]
            elif _BULLET.match(first):
                n = 0
                while n < len(lines) and _BULLET.match(lines[n]):
                    blocks.append(Block("list_item", _BULLET.match(lines[n]).group(1), page=page))
                    n += 1
                lines = lines[n:]
            else:
                n = 0
                while n < len(lines) and not (_HEADING.match(lines[n]) or _BULLET.match(lines[n]) or _is_table(lines[n:])):
                    n += 1
                n = max(n, 1)
                blocks.append(Block("paragraph", "\n".join(ln.strip() for ln in lines[:n]), page=page))
                lines = lines[n:]
    return blocks


def parse_text(data: bytes, filename: str | None = None) -> Document:
    doc = Document(filename=filename, kind="text")
    doc.blocks = markdown_to_blocks(decode_text(data, doc.warnings))
    return doc
