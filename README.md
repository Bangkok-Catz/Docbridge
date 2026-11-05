# docbridge

Document parsing for AI agents, with Thai treated as a first-class language.

Turn PDF, DOCX, HTML, plain text and scanned images into clean **Markdown** and **structured JSON**, then split them into **RAG-ready chunks**. Runs locally, no API keys, no model downloads.

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

## What it does

| Input | How |
|---|---|
| PDF | Text layer via pdfplumber. Headings from font size, paragraphs from line spacing, tables extracted separately and kept in reading order. Pages with no text layer fall back to OCR. |
| DOCX | Walks the body in document order: headings, lists, paragraphs and tables. |
| HTML | Drops scripts, navigation and footers; keeps headings, lists, tables and code. |
| Images | Tesseract OCR with `tha+eng`. |
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
- **OCR quality** depends on Tesseract. Clean scans are good; photos and handwriting are not.
- **Legacy `.doc`, `.xls`, `.pptx`** are not supported yet.

## Roadmap

- XLSX and PPTX parsers
- Optional layout-aware PDF backend for multi-column and scanned tables
- Thai-specific benchmark set (gov forms, invoices, tax documents)
- Structured extraction (key-value fields from invoices and receipts)

## Develop

```bash
pip install -e ".[dev]"
pytest
python tests/make_fixtures.py /path/to/Sarabun-Regular.ttf   # regenerate PDF fixtures
```

## License

MIT
