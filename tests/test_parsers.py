import io
from pathlib import Path

import pytest
from docx import Document as Docx

from docbridge import parse_bytes, parse_file

FIX = Path(__file__).parent / "fixtures"


def test_thai_pdf_headings_paragraphs_tables():
    doc = parse_file(FIX / "thai_sample.pdf")
    assert doc.kind == "pdf" and doc.language == "th" and doc.pages == 1
    types = [b.type for b in doc.blocks]
    assert types[0] == "heading" and "table" in types
    assert doc.blocks[0].text == "รายงานยอดขายประจำไตรมาส"
    assert sum(b.type == "paragraph" for b in doc.blocks) == 2
    table = next(b for b in doc.blocks if b.type == "table")
    assert table.rows[1] == ["เนยพืช", "120", "250"]
    md = doc.to_markdown()
    assert md.startswith("# รายงานยอดขายประจำไตรมาส") and "| --- |" in md


def test_english_pdf():
    doc = parse_file(FIX / "english_sample.pdf")
    assert doc.language == "en"
    assert doc.blocks[0].type == "heading"
    paras = [b.text for b in doc.blocks if b.type == "paragraph"]
    assert len(paras) == 2 and paras[0].startswith("Revenue grew")


def test_kind_is_sniffed_not_trusted_from_extension():
    data = (FIX / "english_sample.pdf").read_bytes()
    assert parse_bytes(data, "report.txt").kind == "pdf"


def _docx_bytes():
    d = Docx()
    d.add_heading("แผนการตลาด", level=1)
    d.add_paragraph("เป้าหมายคือเพิ่มยอดขายออนไลน์")
    d.add_paragraph("ส่งฟรีกรุงเทพฯ", style="List Bullet")
    t = d.add_table(rows=2, cols=2)
    t.cell(0, 0).text, t.cell(0, 1).text = "รายการ", "ราคา"
    t.cell(1, 0).text, t.cell(1, 1).text = "เนยกระเทียม", "250"
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def test_docx_order_and_structure():
    doc = parse_bytes(_docx_bytes(), "plan.docx")
    assert [b.type for b in doc.blocks] == ["heading", "paragraph", "list_item", "table"]
    assert doc.language == "th"
    assert doc.blocks[3].rows[1] == ["เนยกระเทียม", "250"]


def test_html_strips_chrome():
    html = """<html><head><title>T</title><script>x()</script></head><body>
    <nav>menu</nav><main><h1>Hello</h1><p>Body   text</p><ul><li>a</li><li>b</li></ul>
    <table><tr><th>k</th><th>v</th></tr><tr><td>1</td><td>2</td></tr></table></main>
    <footer>foot</footer></body></html>""".encode()
    doc = parse_bytes(html, "p.html")
    assert doc.kind == "html" and doc.metadata["title"] == "T"
    assert "menu" not in doc.text and "foot" not in doc.text
    assert [b.type for b in doc.blocks] == ["heading", "paragraph", "list_item", "list_item", "table"]
    assert doc.blocks[1].text == "Body text"


def test_legacy_cp874_text_decodes():
    raw = "สวัสดีครับ ยินดีต้อนรับ".encode("cp874")
    doc = parse_bytes(raw, "old.txt")
    assert doc.language == "th" and "cp874" in doc.warnings[0]
    assert "สวัสดีครับ" in doc.text


def test_markdown_text_passthrough():
    doc = parse_bytes(b"# Title\n\nSome text.\n\n- one\n- two\n", "a.md")
    assert [b.type for b in doc.blocks] == ["heading", "paragraph", "list_item", "list_item"]


def test_chunks_respect_thai_word_boundaries():
    para = "บริษัทมีรายได้เพิ่มขึ้นจากไตรมาสก่อนหน้าอย่างต่อเนื่องโดยเฉพาะสินค้าในกลุ่มอาหารแช่เย็น" * 6
    doc = parse_bytes(("# หัวข้อ\n\n" + para).encode(), "t.md")
    chunks = doc.chunks(max_chars=120)
    assert len(chunks) > 1
    assert all(len(c.text) <= 120 for c in chunks)
    assert all(c.heading == "หัวข้อ" for c in chunks)
    assert "".join(c.text for c in chunks).replace("\n", "") == para


def test_ocr_roundtrip_if_available():
    from docbridge.parsers.ocr import ocr_available

    if not ocr_available():
        pytest.skip("tesseract not installed")
    pdfplumber = pytest.importorskip("pdfplumber")
    with pdfplumber.open(FIX / "english_sample.pdf") as pdf:
        img = pdf.pages[0].to_image(resolution=200).original
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    doc = parse_bytes(buf.getvalue(), "scan.png")
    assert doc.kind == "image" and "Quarterly" in doc.text
