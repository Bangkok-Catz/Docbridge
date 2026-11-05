"""LFM3-VL integration, tested against a fake OpenAI-compatible server.

The fake mimics llama.cpp serving LiquidAI/LFM3-VL-2B-GGUF, including the
<think> block LFM3 emits before answering.
"""
import io
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from PIL import Image

from docbridge import parse_bytes
from docbridge.parsers.pdf import garbled_ratio
from docbridge.vlm import clean_output, reset_backend

FAKE_REPLY = """<think>The page has a Thai title, a sentence and a table.</think>
```markdown
# ใบแจ้งหนี้

ขอบคุณที่ใช้บริการ

| รายการ | ราคา |
| --- | --- |
| เนยกระเทียม | 250 |
```"""


class _Handler(BaseHTTPRequestHandler):
    requests: list = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        _Handler.requests.append((self.path, body, self.headers.get("Authorization")))
        out = json.dumps({"choices": [{"message": {"content": FAKE_REPLY}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


@pytest.fixture
def fake_lfm3(monkeypatch):
    srv = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    _Handler.requests = []
    monkeypatch.setenv("DOCBRIDGE_VLM", "http")
    monkeypatch.setenv("DOCBRIDGE_VLM_URL", f"http://127.0.0.1:{srv.server_port}/v1")
    monkeypatch.setenv("DOCBRIDGE_VLM_API_KEY", "k")
    reset_backend()
    yield _Handler.requests
    srv.shutdown()
    reset_backend()


def _png(w=2400, h=3200):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), "white").save(buf, format="PNG")
    return buf.getvalue()


def test_clean_output_strips_think_and_fence():
    assert clean_output(FAKE_REPLY).startswith("# ใบแจ้งหนี้")
    assert clean_output("partial reasoning</think>\nHello") == "Hello"


def test_image_goes_through_lfm3(fake_lfm3):
    doc = parse_bytes(_png(), "scan.png")
    assert doc.metadata["ocr_engine"] == "lfm3-vl (http)"
    assert [b.type for b in doc.blocks] == ["heading", "paragraph", "table"]
    assert doc.blocks[2].rows == [["รายการ", "ราคา"], ["เนยกระเทียม", "250"]]
    assert doc.language == "th"

    path, body, auth = fake_lfm3[0]
    assert path == "/v1/chat/completions" and auth == "Bearer k"
    assert body["model"] == "LiquidAI/LFM3-VL-2B" and body["temperature"] == 0.1
    img_part = body["messages"][0]["content"][0]["image_url"]["url"]
    sent = Image.open(io.BytesIO(__import__("base64").b64decode(img_part.split(",", 1)[1])))
    assert max(sent.size) <= 1800  # downscaled before sending


def test_scanned_pdf_page_uses_lfm3(fake_lfm3):
    buf = io.BytesIO()
    Image.new("RGB", (600, 800), "white").save(buf, format="PDF")
    doc = parse_bytes(buf.getvalue(), "scan.pdf")
    assert doc.kind == "pdf" and doc.blocks[0].text == "ใบแจ้งหนี้"
    assert any("no text layer" in w and "lfm3-vl" in w for w in doc.warnings)


def test_tesseract_engine_skips_vlm(fake_lfm3):
    parse_bytes(_png(400, 300), "scan.png", ocr_engine="tesseract")
    assert fake_lfm3 == []


def test_falls_back_to_tesseract_when_server_down(monkeypatch):
    monkeypatch.setenv("DOCBRIDGE_VLM", "http")
    monkeypatch.setenv("DOCBRIDGE_VLM_URL", "http://127.0.0.1:9/v1")
    reset_backend()
    try:
        doc = parse_bytes(_png(400, 300), "scan.png")
        assert any("failed" in w and "falling back" in w for w in doc.warnings)
    finally:
        reset_backend()


def test_vlm_requested_but_not_configured(monkeypatch):
    monkeypatch.delenv("DOCBRIDGE_VLM", raising=False)
    reset_backend()
    doc = parse_bytes(_png(400, 300), "scan.png", ocr_engine="vlm")
    assert any("not configured" in w for w in doc.warnings)


def test_garbled_detection():
    assert garbled_ratio("(cid:123)(cid:45)(cid:67) abc") > 0.5
    assert garbled_ratio(" ก") > 0.5
    assert garbled_ratio("รายงานยอดขายประจำไตรมาส") == 0.0


def test_markdown_pipe_tables_in_text_files():
    doc = parse_bytes("| a | b |\n|---|---|\n| 1 | 2 |\n".encode(), "t.md")
    assert doc.blocks[0].type == "table" and doc.blocks[0].rows == [["a", "b"], ["1", "2"]]
