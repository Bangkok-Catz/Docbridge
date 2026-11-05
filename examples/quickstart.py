"""Parse a file, print Markdown, then get RAG-ready chunks.

    python examples/quickstart.py tests/fixtures/thai_sample.pdf
"""
import sys

from docbridge import parse_file

doc = parse_file(sys.argv[1])
print(f"kind={doc.kind} language={doc.language} pages={doc.pages}")
print(doc.to_markdown())

for i, c in enumerate(doc.chunks(max_chars=400)):
    print(f"--- chunk {i} (heading: {c.heading}, page: {c.page}) ---")
    print(c.text)
