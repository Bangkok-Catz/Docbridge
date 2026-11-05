from pathlib import Path

from fastapi.testclient import TestClient

from docbridge.api import app

FIX = Path(__file__).parent / "fixtures"
client = TestClient(app)


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_parse_thai_pdf():
    with open(FIX / "thai_sample.pdf", "rb") as f:
        r = client.post("/v1/parse", files={"file": ("thai_sample.pdf", f, "application/pdf")})
    assert r.status_code == 200
    body = r.json()
    assert body["language"] == "th" and body["markdown"].startswith("# รายงาน")


def test_chunk_endpoint():
    with open(FIX / "english_sample.pdf", "rb") as f:
        r = client.post("/v1/chunk?max_chars=200", files={"file": ("e.pdf", f, "application/pdf")})
    assert r.status_code == 200 and r.json()["chunks"]


def test_api_key_enforced(monkeypatch):
    monkeypatch.setenv("DOCBRIDGE_API_KEY", "secret")
    files = {"file": ("a.txt", b"hello world", "text/plain")}
    assert client.post("/v1/parse", files=files).status_code == 401
    assert client.post("/v1/parse", files=files, headers={"X-API-Key": "secret"}).status_code == 200


def test_size_limit(monkeypatch):
    monkeypatch.setenv("DOCBRIDGE_MAX_MB", "0.0001")
    r = client.post("/v1/parse", files={"file": ("a.txt", b"x" * 5000, "text/plain")})
    assert r.status_code == 413


def test_corrupt_pdf_is_422():
    r = client.post("/v1/parse", files={"file": ("bad.pdf", b"%PDF-1.4 garbage", "application/pdf")})
    assert r.status_code == 422
