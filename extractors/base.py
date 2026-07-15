"""Unified data structures for table extraction backends."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExtractedTable:
    """A single extracted table."""
    page_number: int
    table_index: int
    rows: list[list[str]]
    flavor: str | None = None
    accuracy: float | None = None
    whitespace: float | None = None
    source_backend: str = ""
    raw: Any = None


@dataclass
class ExtractedPage:
    """A single page with text and tables."""
    page_number: int
    text: str = ""
    tables: list[ExtractedTable] = field(default_factory=list)


@dataclass
class ExtractedDocument:
    """A complete document with all pages."""
    document_id: str
    file_name: str
    pages: list[ExtractedPage]
    source_backend: str
