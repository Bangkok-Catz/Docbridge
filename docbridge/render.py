"""Blocks to Markdown."""
from __future__ import annotations

from .models import Block


def _cell(s: str) -> str:
    return (s or "").replace("|", "\\|").replace("\n", " ").strip()


def table_to_markdown(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    norm = [[_cell(c) for c in r] + [""] * (width - len(r)) for r in rows]
    out = ["| " + " | ".join(norm[0]) + " |", "| " + " | ".join("---" for _ in range(width)) + " |"]
    out.extend("| " + " | ".join(r) + " |" for r in norm[1:])
    return "\n".join(out)


def blocks_to_markdown(blocks: list[Block]) -> str:
    parts: list[str] = []
    prev_list = False
    for b in blocks:
        if b.type == "heading":
            parts.append("#" * max(1, min(b.level or 1, 6)) + " " + b.text)
            prev_list = False
        elif b.type == "list_item":
            line = "- " + b.text
            if prev_list and parts:
                parts[-1] += "\n" + line
            else:
                parts.append(line)
            prev_list = True
        elif b.type == "table":
            parts.append(table_to_markdown(b.rows))
            prev_list = False
        elif b.type == "code":
            parts.append("```\n" + b.text + "\n```")
            prev_list = False
        else:
            parts.append(b.text)
            prev_list = False
    return "\n\n".join(p for p in parts if p).strip() + "\n"
