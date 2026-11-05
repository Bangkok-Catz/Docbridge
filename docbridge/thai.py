"""Thai text cleanup and segmentation.

PDF and OCR extraction routinely damage Thai text in ways English never sees:
decomposed sara am, zero-width characters, stray spaces between letters, and
doubled combining marks. normalize_thai() repairs the common cases.
"""
from __future__ import annotations

import re
import unicodedata

from .detect import is_thai_char

_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍⁠﻿"), None)
# Thai combining marks: mai han-akat, vowels above/below, tone marks, etc.
_COMBINING = "ัิีึืฺุู็่้๊๋์ํ๎"
_DOUBLED_MARK = re.compile(f"([{_COMBINING}])\\1+")
_THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
# a Thai char, then (space + 1-2 Thai chars) repeated: typical of letter-spaced extraction
_SPACED_RUN = re.compile(r"(?:(?<=[฀-๿]) (?=[฀-๿]))")


def _looks_letter_spaced(line: str) -> bool:
    """True when most Thai tokens in the line are 1-2 characters long.

    Real Thai text separates phrases with spaces, but tokens are several
    characters long. Extraction artifacts produce "ก า ร ท ด ส อ บ".
    """
    tokens = [t for t in line.split(" ") if t]
    thai_tokens = [t for t in tokens if any(is_thai_char(c) for c in t)]
    if len(thai_tokens) < 4:
        return False
    short = sum(1 for t in thai_tokens if len(t) <= 2)
    return short / len(thai_tokens) >= 0.7


def normalize_thai(text: str, *, thai_digits: bool = False) -> str:
    """Repair common Thai extraction damage. Safe to run on English text."""
    if not any(is_thai_char(c) for c in text):
        return text
    text = unicodedata.normalize("NFC", text)
    text = text.translate(_ZERO_WIDTH)
    # nikhahit + sara aa should be the single sara am character
    text = text.replace("ํา", "ำ")
    text = _DOUBLED_MARK.sub(r"\1", text)
    lines = []
    for line in text.split("\n"):
        if _looks_letter_spaced(line):
            line = _SPACED_RUN.sub("", line)
        lines.append(line)
    text = "\n".join(lines)
    if thai_digits:
        text = text.translate(_THAI_DIGITS)
    return text


def segment(text: str) -> list[str]:
    """Split Thai/English text into words using PyThaiNLP (newmm engine)."""
    from pythainlp.tokenize import word_tokenize

    return [w for w in word_tokenize(text, engine="newmm", keep_whitespace=False) if w.strip()]
