# docbridge

Document parsing for AI agents, with Thai treated as a first-class language.

Turn PDF, DOCX, HTML, plain text and scanned images into clean **Markdown** and **structured JSON**, then split them into **RAG-ready chunks**. Runs locally with no API keys. Optionally uses Liquid AI's **LFM3-VL-2B** vision model for scanned and broken-font pages.

## Why

Most parsing tools are built and tested on English. Thai breaks them in quiet ways:

- Words are not separated by spaces, so naive chunking cuts words in half.
- PDF and OCR extraction produces decomposed *sara am* (`ํ` + `า` instead of `ำ`), zero-width characters, doubled tone marks, and letter-spaced text (`ก า ร ท ด ส อ บ`).
- Older Thai documents are often `cp874`, not UTF-8.
- Thai and English are frequently mixed in the same document.

docbridge repairs these and detects language by script, so downstream LLMs and embedding models see clean text.

## Install

```bash
pip install -e ".[api,ocr]"
```

Extras: `api` (FastAPI server), `ocr` (scanned pages and images). For OCR also install Tesseract with the Thai pack:

```bash
sudo apt-get install tesseract-ocr tesseract-ocr-tha tesseract-ocr-eng
```

## Use it

**Python**

```python
from docbridge import parse_file

doc = parse_file("report.pdf")
print(doc.language)        # "th", "en", "mixed" or "unknown"
print(doc.to_markdown())   # headings, paragraphs, lists, tables
doc.to_dict()              # structured blocks as JSON-ready data

for chunk in doc.chunks(max_chars=1200):   # never cuts a Thai word in half
    print(chunk.heading, chunk.page, chunk.text)
```

**CLI**

```bash
docbridge parse report.pdf                    # Markdown
docbridge parse report.pdf --format json      # structured blocks
docbridge parse report.pdf --format chunks --chunk-size 800
docbridge parse scan.png                      # OCR (Thai + English)
```

**HTTP API**

```bash
docbridge serve --port 8000
curl -F file=@report.pdf http://localhost:8000/v1/parse
curl -F file=@report.pdf "http://localhost:8000/v1/chunk?max_chars=800"
```

Set `DOCBRIDGE_API_KEY` to require an `X-API-Key` header, and `DOCBRIDGE_MAX_MB` to change the upload limit (default 25).

**Docker** (includes Tesseract with Thai)

```bash
docker build -t docbridge . && docker run -p 8000:8000 docbridge
```

## AI OCR with Liquid AI LFM3-VL-2B (optional)

Tesseract struggles with Thai: tone marks get dropped, tables turn into loose text, and photos fail. docbridge can hand those pages to **[LFM3-VL-2B](https://huggingface.co/LiquidAI/LFM3-VL-2B)** instead. It's a ~2B open-weight vision model from Liquid AI (released Oct 2026) that lists Thai among its 16 languages, runs on a laptop CPU (about 1.1 GB at Q4_K_M), and returns Markdown with real tables.

docbridge uses it only where it helps:

- **Images** (photos, screenshots, scans)
- **PDF pages with no text layer** (scanned documents)
- **PDF pages with a garbled text layer**. Many Thai PDFs embed fonts without a usable Unicode map, so text extracts as `(cid:123)` codes or private-use glyphs. docbridge detects this and re-reads the page visually.

Normal digital PDFs, DOCX and HTML never touch the model, so they stay fast.

**Option A: llama.cpp server (recommended)**

```bash
llama serve -hf LiquidAI/LFM3-VL-2B-GGUF:Q4_K_M        # OpenAI-compatible on :8080
export DOCBRIDGE_VLM=http
docbridge parse scanned-invoice.pdf
```

Any OpenAI-compatible server works (vLLM, LM Studio, Liquid's API). Point to it with `DOCBRIDGE_VLM_URL` (default `http://localhost:8080/v1`), and set `DOCBRIDGE_VLM_MODEL` and `DOCBRIDGE_VLM_API_KEY` if needed.

**Option B: in-process with transformers**

```bash
pip install -e ".[vlm]"
export DOCBRIDGE_VLM=transformers
```

**Option C: everything in Docker**

```bash
docker compose up        # docbridge on :8000, LFM3-VL-2B on :8080
```

Choose the engine per request with `--ocr-engine auto|vlm|tesseract` (CLI) or `?ocr_engine=` (API). `auto` uses LFM3 when configured, otherwise Tesseract. If the model server is down, docbridge falls back to Tesseract and adds a warning. The engine used is reported in `metadata.ocr_engine`, and `/health` shows whether the VLM is active.

> **License note:** docbridge is MIT. LFM3 weights are under the separate **LFM Open License v1.0**: free for commercial use by companies under US$10M annual revenue, with a paid license required above that. You download and run the weights yourself; docbridge does not bundle them.

## What it does

| Input | How |
|---|---|
| PDF | Text layer via pdfplumber. Headings from font size, paragraphs from line spacing, tables extracted separately and kept in reading order. Pages with no text layer, or with garbled Thai font encoding, are re-read with OCR. |
| DOCX | Walks the body in document order: headings, lists, paragraphs and tables. |
| HTML | Drops scripts, navigation and footers; keeps headings, lists, tables and code. |
| Images | LFM3-VL-2B if configured, otherwise Tesseract OCR with `tha+eng`. |
| Text / Markdown | Handles UTF-8 and legacy `cp874`. |

File type is detected from content, not the extension.

## Output shape

```json
{
  "kind": "pdf",
  "language": "th",
  "language_ratio": {"th": 1.0, "en": 0.0},
  "pages": 1,
  "blocks": [
    {"type": "heading", "text": "รายงานยอดขายประจำไตรมาส", "level": 1, "page": 1},
    {"type": "table", "rows": [["สินค้า", "จำนวน"], ["เนยพืช", "120"]], "page": 1}
  ],
  "warnings": []
}
```

Block types: `heading`, `paragraph`, `list_item`, `table`, `code`. Anything the parser could not do well (scanned pages without OCR, legacy encodings) is reported in `warnings` instead of failing silently.

## Known limits

- **No layout model.** Multi-column PDFs, text boxes and complex nested tables can come out in the wrong order. A layout-model backend is the main planned upgrade.
- **Thai line joining.** When a PDF line wraps, Thai lines are joined with no space because the source rarely says whether one existed. The text is correct for LLMs and search but may lose a phrase-level space at wrap points.
- **OCR quality.** Tesseract is fine for clean scans; use LFM3-VL-2B for photos, tables and Thai. LFM3 is a small model, so very dense pages can still have errors. Each page is sent to it as a separate request.
- **Legacy `.doc`, `.xls`, `.pptx`** are not supported yet.

## Roadmap

- XLSX and PPTX parsers
- Use LFM3-VL-2B for multi-column PDF reading order
- Structured field extraction with LFM3 (invoice and receipt fields to JSON)
- Thai-specific benchmark set (gov forms, invoices, tax documents)

## Develop

```bash
pip install -e ".[dev]"
pytest
python tests/make_fixtures.py /path/to/Sarabun-Regular.ttf   # regenerate PDF fixtures
```

## License

MIT
