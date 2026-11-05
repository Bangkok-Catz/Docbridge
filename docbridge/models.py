"""Data model returned by every parser."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Block:
    """One structural element of a document.

    type is one of: heading, paragraph, list_item, table, code.
    """

    type: str
    text: str = ""
    level: int = 0  # heading level (1-6)
    rows: list[list[str]] = field(default_factory=list)  # table cells
    page: int | None = None


@dataclass
class Document:
    filename: str | None = None
    kind: str = "text"  # pdf, docx, html, image, text
    language: str = "unknown"  # th, en, mixed, unknown
    language_ratio: dict[str, float] = field(default_factory=dict)
    pages: int | None = None
    blocks: list[Block] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    # ---- output helpers -------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_markdown(self) -> str:
        from .render import blocks_to_markdown

        return blocks_to_markdown(self.blocks)

    @property
    def text(self) -> str:
        parts: list[str] = []
        for b in self.blocks:
            if b.type == "table":
                parts.extend(" | ".join(r) for r in b.rows)
            elif b.text:
                parts.append(b.text)
        return "\n\n".join(parts)

    def chunks(self, max_chars: int = 1200):
        from .chunk import chunk_document

        return chunk_document(self, max_chars=max_chars)
