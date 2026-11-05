"""docbridge: document parsing for AI agents, with first-class Thai support."""
from .core import parse_bytes, parse_file
from .models import Block, Document
from .thai import normalize_thai, segment

__all__ = ["parse_bytes", "parse_file", "Document", "Block", "normalize_thai", "segment"]
__version__ = "0.1.0"
