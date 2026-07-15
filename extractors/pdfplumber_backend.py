"""pdfplumber-based table extraction backend.

Reuses existing pipeline/extractor.py logic but wraps output in
the unified ExtractedDocument / ExtractedPage / ExtractedTable format.
"""

import re
import hashlib
from pathlib import Path

import pdfplumber

from extractors.base import ExtractedTable, ExtractedPage, ExtractedDocument


def _clean_cell(text: str) -> str:
    """Clean a single cell text."""
    if not text:
        return ""
    # Replace newlines with spaces
    text = text.replace("\n", " ").replace("\r", " ")
    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _make_doc_id(pdf_path: str) -> str:
    """Generate a document ID from PDF path."""
    path_bytes = pdf_path.encode("utf-8")
    return hashlib.md5(path_bytes).hexdigest()[:12]


def extract_with_pdfplumber(pdf_path: str, pages: str = "all") -> ExtractedDocument:
    """Extract text and tables from PDF using pdfplumber.

    Args:
        pdf_path: Path to the PDF file.
        pages: Page spec passed to pdfplumber (e.g. "1,2" or "all").

    Returns:
        ExtractedDocument with all pages and tables.
    """
    doc_id = _make_doc_id(pdf_path)
    file_name = Path(pdf_path).name
    source_backend = "pdfplumber"

    pages_out: list[ExtractedPage] = []

    with pdfplumber.open(pdf_path) as pdf:
        # Determine which pages to process
        if pages == "all":
            page_indices = range(len(pdf.pages))
        else:
            # Parse page spec like "1,2,3" or "1-3"
            page_indices = []
            for part in pages.split(","):
                part = part.strip()
                if "-" in part:
                    start, end = part.split("-", 1)
                    page_indices.extend(range(int(start.strip()) - 1, int(end.strip())))
                else:
                    page_indices.append(int(part) - 1)

        for pi in page_indices:
            if pi < 0 or pi >= len(pdf.pages):
                continue

            page_obj = pdf.pages[pi]
            page_num = pi + 1

            # Extract text
            text = page_obj.extract_text() or ""

            # Extract tables
            tables_out: list[ExtractedTable] = []
            raw_tables = page_obj.extract_tables()

            for ti, raw_table in enumerate(raw_tables):
                if not raw_table:
                    continue

                # Clean each cell
                cleaned_rows: list[list[str]] = []
                for row in raw_table:
                    cleaned_row = [_clean_cell(str(cell)) if cell else "" for cell in row]
                    # Skip fully empty rows
                    if any(c for c in cleaned_row):
                        cleaned_rows.append(cleaned_row)

                table = ExtractedTable(
                    page_number=page_num,
                    table_index=ti,
                    rows=cleaned_rows,
                    flavor="pdfplumber",
                    source_backend="pdfplumber",
                )
                tables_out.append(table)

            pages_out.append(ExtractedPage(
                page_number=page_num,
                text=text,
                tables=tables_out,
            ))

    return ExtractedDocument(
        document_id=doc_id,
        file_name=file_name,
        pages=pages_out,
        source_backend=source_backend,
    )
