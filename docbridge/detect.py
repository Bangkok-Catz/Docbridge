"""Language and file-type detection (no network, no heavy models)."""
from __future__ import annotations

import io
import zipfile

THAI_START, THAI_END = "฀", "๿"


def is_thai_char(ch: str) -> bool:
    return THAI_START <= ch <= THAI_END


def detect_language(text: str) -> tuple[str, dict[str, float]]:
    """Classify text by script. Returns (label, ratios).

    Label is "th", "en", "mixed" or "unknown". Ratios are over letters only.
    Thai has no spaces between words, so script ratio is far more reliable
    than word-based detectors for this pair.
    """
    thai = latin = 0
    for ch in text:
        if is_thai_char(ch):
            if ch.isalpha():
                thai += 1
        elif ch.isascii() and ch.isalpha():
            latin += 1
    total = thai + latin
    if total < 3:
        return "unknown", {"th": 0.0, "en": 0.0}
    ratios = {"th": round(thai / total, 3), "en": round(latin / total, 3)}
    if ratios["th"] >= 0.85:
        return "th", ratios
    if ratios["en"] >= 0.85:
        return "en", ratios
    return "mixed", ratios


def sniff_kind(data: bytes, filename: str | None = None) -> str:
    """Decide the file kind from magic bytes, falling back to the extension."""
    head = data[:2048]
    if head.startswith(b"%PDF"):
        return "pdf"
    if head.startswith((b"\x89PNG", b"\xff\xd8\xff", b"II*\x00", b"MM\x00*", b"BM")) or head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image"
    if head.startswith(b"PK"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                if any(n.startswith("word/") for n in z.namelist()):
                    return "docx"
        except zipfile.BadZipFile:
            pass
    lowered = head.lstrip().lower()
    if lowered.startswith((b"<!doctype html", b"<html")) or b"<body" in lowered[:1024]:
        return "html"
    if filename:
        ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
        if ext in {"html", "htm"}:
            return "html"
        if ext in {"docx"}:
            return "docx"
        if ext in {"pdf"}:
            return "pdf"
        if ext in {"png", "jpg", "jpeg", "tif", "tiff", "bmp", "webp"}:
            return "image"
    return "text"
