"""Regenerate tests/fixtures/*.pdf.

Usage: python tests/make_fixtures.py /path/to/Sarabun-Regular.ttf
(Sarabun is SIL OFL: https://github.com/google/fonts/tree/main/ofl/sarabun)
The font is NOT committed; only the small generated PDFs are.
"""
import sys
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table
from reportlab.lib.styles import ParagraphStyle

out = Path(__file__).parent / "fixtures"
out.mkdir(exist_ok=True)
pdfmetrics.registerFont(TTFont("Sarabun", sys.argv[1]))

h1 = ParagraphStyle("h1", fontName="Sarabun", fontSize=24, leading=30)
body = ParagraphStyle("body", fontName="Sarabun", fontSize=12, leading=16, spaceAfter=10)


def build(name, title, paras, rows):
    story = [Paragraph(title, h1), Spacer(1, 12)]
    story += [Paragraph(p, body) for p in paras]
    story += [Spacer(1, 12), Table(rows, style=[("FONT", (0, 0), (-1, -1), "Sarabun"), ("GRID", (0, 0), (-1, -1), 0.5, "black")])]
    SimpleDocTemplate(str(out / name), pagesize=A4).build(story)


build(
    "thai_sample.pdf",
    "รายงานยอดขายประจำไตรมาส",
    ["บริษัทมีรายได้เพิ่มขึ้นจากไตรมาสก่อนหน้าอย่างต่อเนื่อง โดยเฉพาะสินค้าในกลุ่มอาหารแช่เย็น",
     "ทีมงานวางแผนขยายช่องทางการจัดส่งไปยังต่างจังหวัดภายในสิ้นปีนี้"],
    [["สินค้า", "จำนวน", "ราคา"], ["เนยพืช", "120", "250"], ["ไอศกรีม", "300", "90"]],
)
build(
    "english_sample.pdf",
    "Quarterly Sales Report",
    ["Revenue grew steadily over the previous quarter, driven mainly by chilled food products.",
     "The team plans to extend delivery to provincial areas before the end of the year."],
    [["Product", "Units", "Price"], ["Plant butter", "120", "250"], ["Gelato", "300", "90"]],
)
print("wrote", list(out.glob("*.pdf")))
