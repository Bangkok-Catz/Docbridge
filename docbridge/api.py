"""HTTP API. Run with `docbridge serve` or `uvicorn docbridge.api:app`.

Environment:
  DOCBRIDGE_API_KEY   if set, requests must send it in the X-API-Key header
  DOCBRIDGE_MAX_MB    upload size limit in MB (default 25)
  DOCBRIDGE_VLM       "http" or "transformers" to enable LFM3-VL-2B OCR (see docbridge/vlm.py)
"""
from __future__ import annotations

import hmac
import os

from typing import Literal

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile

from . import __version__
from .core import parse_bytes

app = FastAPI(title="docbridge", version=__version__, description="Document parsing for AI agents. Thai + English.")


def _auth(x_api_key: str | None = Header(default=None)):
    expected = os.environ.get("DOCBRIDGE_API_KEY")
    if expected and not hmac.compare_digest(x_api_key or "", expected):
        raise HTTPException(401, "invalid or missing X-API-Key")


async def _read(file: UploadFile) -> bytes:
    limit = int(float(os.environ.get("DOCBRIDGE_MAX_MB", "25")) * 1024 * 1024)
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"file exceeds {limit // (1024 * 1024)} MB limit")
    if not data:
        raise HTTPException(400, "empty file")
    return data


@app.get("/health")
def health():
    from .vlm import get_backend

    backend = get_backend()
    return {"status": "ok", "version": __version__, "vlm": backend.name if backend else None}


@app.post("/v1/parse", dependencies=[Depends(_auth)])
async def parse(
    file: UploadFile = File(...),
    ocr: bool = Query(True, description="use OCR for scanned pages and images"),
    thai_digits: bool = Query(False, description="convert Thai digits to Arabic digits"),
    ocr_engine: Literal["auto", "vlm", "tesseract"] = Query("auto", description="auto = LFM3-VL-2B if configured, else Tesseract"),
):
    """Parse a file into structured blocks plus a Markdown rendering."""
    data = await _read(file)
    try:
        doc = parse_bytes(data, file.filename, ocr=ocr, thai_digits=thai_digits, ocr_engine=ocr_engine)
    except Exception as exc:  # corrupt or unsupported input
        raise HTTPException(422, f"could not parse file: {exc}") from exc
    out = doc.to_dict()
    out["markdown"] = doc.to_markdown()
    return out


@app.post("/v1/chunk", dependencies=[Depends(_auth)])
async def chunk(
    file: UploadFile = File(...),
    max_chars: int = Query(1200, ge=100, le=20000),
    ocr: bool = True,
    ocr_engine: Literal["auto", "vlm", "tesseract"] = "auto",
):
    """Parse and split into RAG-ready chunks (Thai-aware)."""
    data = await _read(file)
    try:
        doc = parse_bytes(data, file.filename, ocr=ocr, ocr_engine=ocr_engine)
    except Exception as exc:
        raise HTTPException(422, f"could not parse file: {exc}") from exc
    return {
        "language": doc.language,
        "warnings": doc.warnings,
        "chunks": [c.__dict__ for c in doc.chunks(max_chars)],
    }
