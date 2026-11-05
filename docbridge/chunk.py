"""Chunking for RAG, aware that Thai has no spaces between words."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .detect import is_thai_char
from .models import Document

_SENTENCE_END = re.compile(r"(?<=[.!?。])\s+")


@dataclass
class Chunk:
    text: str
    heading: str | None = None  # nearest preceding heading
    page: int | None = None


def _has_thai(s: str) -> bool:
    return any(is_thai_char(c) for c in s)


def _split_long(text: str, max_chars: int) -> list[str]:
    """Split one oversized paragraph. Thai breaks on word boundaries, not mid-word."""
    if len(text) <= max_chars:
        return [text]
    pieces: list[str] = []
    for sent in _SENTENCE_END.split(text):
        if len(sent) <= max_chars:
            pieces.append(sent)
            continue
        if _has_thai(sent):
            from .thai import segment

            words = segment(sent)
            joiner = ""
        else:
            words = sent.split(" ")
            joiner = " "
        cur = ""
        for w in words:
            if cur and len(cur) + len(joiner) + len(w) > max_chars:
                pieces.append(cur)
                cur = w
            else:
                cur = cur + joiner + w if cur else w
        if cur:
            pieces.append(cur)
    # re-pack small neighbours
    packed: list[str] = []
    for p in pieces:
        if packed and len(packed[-1]) + 1 + len(p) <= max_chars:
            packed[-1] = packed[-1] + (" " if not _has_thai(p) else "") + p
        else:
            packed.append(p)
    return packed


def chunk_document(doc: Document, max_chars: int = 1200) -> list[Chunk]:
    chunks: list[Chunk] = []
    heading: str | None = None
    buf: list[str] = []
    buf_page: int | None = None

    def flush():
        nonlocal buf, buf_page
        if buf:
            chunks.append(Chunk("\n\n".join(buf), heading, buf_page))
        buf, buf_page = [], None

    for b in doc.blocks:
        if b.type == "heading":
            flush()
            heading = b.text
            continue
        if b.type == "table":
            from .render import table_to_markdown

            text = table_to_markdown(b.rows)
        else:
            text = b.text
        if not text:
            continue
        for piece in _split_long(text, max_chars):
            if buf and sum(len(x) for x in buf) + len(piece) + 2 > max_chars:
                flush()
            if not buf:
                buf_page = b.page
            buf.append(piece)
    flush()
    return chunks
