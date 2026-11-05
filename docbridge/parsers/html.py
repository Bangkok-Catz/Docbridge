"""HTML parser: strips chrome (nav, scripts, footers) and keeps structure."""
from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

from ..models import Block, Document
from .text import decode_text

_DROP = ["script", "style", "noscript", "nav", "footer", "aside", "form", "svg", "iframe"]
_BLOCKS = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "table", "pre", "blockquote"}


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def parse_html(data: bytes, filename: str | None = None) -> Document:
    doc = Document(filename=filename, kind="html")
    soup = BeautifulSoup(decode_text(data, doc.warnings), "lxml")
    if soup.title and soup.title.string:
        doc.metadata["title"] = _clean(soup.title.string)
    for tag in soup(_DROP):
        tag.decompose()
    root = soup.find("main") or soup.find("article") or soup.body or soup

    def walk(node: Tag):
        for child in node.children:
            if not isinstance(child, Tag):
                continue
            name = child.name
            if name in _BLOCKS:
                if name.startswith("h"):
                    t = _clean(child.get_text(" "))
                    if t:
                        doc.blocks.append(Block("heading", t, level=int(name[1])))
                elif name == "li":
                    t = _clean(child.get_text(" "))
                    if t:
                        doc.blocks.append(Block("list_item", t))
                elif name == "table":
                    rows = [
                        [_clean(c.get_text(" ")) for c in tr.find_all(["th", "td"])]
                        for tr in child.find_all("tr")
                    ]
                    rows = [r for r in rows if any(r)]
                    if rows:
                        doc.blocks.append(Block("table", rows=rows))
                elif name == "pre":
                    doc.blocks.append(Block("code", child.get_text().strip("\n")))
                else:
                    t = _clean(child.get_text(" "))
                    if t:
                        doc.blocks.append(Block("paragraph", t))
            else:
                walk(child)

    walk(root)
    return doc
