"""Command line: `docbridge parse file.pdf` and `docbridge serve`."""
from __future__ import annotations

import argparse
import json
import sys

from .core import parse_file


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="docbridge", description="Parse documents to Markdown/JSON (Thai + English).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("parse", help="parse a file")
    p.add_argument("file")
    p.add_argument("--format", choices=["md", "json", "chunks"], default="md")
    p.add_argument("--chunk-size", type=int, default=1200, help="max characters per chunk (chunks format)")
    p.add_argument("--no-ocr", action="store_true")
    p.add_argument("--thai-digits", action="store_true", help="convert Thai digits to Arabic digits")

    s = sub.add_parser("serve", help="run the HTTP API (needs the 'api' extra)")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8000)

    args = ap.parse_args(argv)

    if args.cmd == "serve":
        import uvicorn

        uvicorn.run("docbridge.api:app", host=args.host, port=args.port)
        return 0

    doc = parse_file(args.file, ocr=not args.no_ocr, thai_digits=args.thai_digits)
    for w in doc.warnings:
        print(f"warning: {w}", file=sys.stderr)
    if args.format == "md":
        sys.stdout.write(doc.to_markdown())
    elif args.format == "json":
        json.dump(doc.to_dict(), sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        out = [c.__dict__ for c in doc.chunks(args.chunk_size)]
        json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
