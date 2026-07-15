"""Camelot-based table extraction backend.

Supports both 'lattice' and 'stream' flavors.
"""

import re
import hashlib
import logging
from pathlib import Path
from typing import Optional

from extractors.base import ExtractedTable, ExtractedPage, ExtractedDocument

logger = logging.getLogger(__name__)

# Camelot is an optional dependency
try:
    import camelot
    CAMELOT_AVAILABLE = True
except ImportError:
    CAMELOT_AVAILABLE = False
    camelot = None


def _make_doc_id(pdf_path: str) -> str:
    """Generate a document ID from PDF path."""
    path_bytes = pdf_path.encode("utf-8")
    return hashlib.md5(path_bytes).hexdigest()[:12]


def _clean_cell(text: str) -> str:
    """Clean a single cell text."""
    if not text:
        return ""
    # Replace newlines with spaces
    text = text.replace("\n", " ").replace("\r", " ")
    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_tables_from_camelot_tables(
    camelot_tables: list,
    page_number: int,
    flavor: str,
) -> list[ExtractedTable]:
    """Convert Camelot table objects to ExtractedTable list."""
    tables = []
    for ti, camelot_table in enumerate(camelot_tables):
        if camelot_table.df is None or camelot_table.df.empty:
            continue

        # Get parsing report
        parsing_report = camelot_table.parsing_report
        accuracy = parsing_report.get("accuracy")
        whitespace = parsing_report.get("whitespace", 0.0)

        # Convert DataFrame to list of lists
        rows: list[list[str]] = []
        for _, row in camelot_table.df.iterrows():
            cleaned_row = []
            for cell in row:
                cleaned_row.append(_clean_cell(str(cell)) if cell is not None else "")
            rows.append(cleaned_row)

        table = ExtractedTable(
            page_number=page_number,
            table_index=ti,
            rows=rows,
            flavor=flavor,
            accuracy=accuracy,
            whitespace=whitespace,
            source_backend="camelot",
            raw=camelot_table,
        )
        tables.append(table)

    return tables


def extract_with_camelot(pdf_path: str, pages: str = "all") -> ExtractedDocument:
    """Extract text and tables from PDF using Camelot.

    Tries both 'lattice' and 'stream' flavors, collecting all tables
    found without raising errors if one flavor fails.

    Args:
        pdf_path: Path to the PDF file.
        pages: Page spec passed to Camelot (e.g. "1,2" or "all").

    Returns:
        ExtractedDocument with all pages and tables from both flavors.
    """
    doc_id = _make_doc_id(pdf_path)
    file_name = Path(pdf_path).name

    if not CAMELOT_AVAILABLE:
        logger.warning("Camelot is not available. Install with: pip install camelot-py")
        return ExtractedDocument(
            document_id=doc_id,
            file_name=file_name,
            pages=[],
            source_backend="camelot",
        )

    # Camelot page format: "1-end" or "all"
    camelot_pages = pages if pages != "all" else "all"

    all_tables: list[ExtractedTable] = []
    errors: list[str] = []

    # Try lattice flavor
    try:
        lattice_result = camelot.read_pdf(pdf_path, pages=camelot_pages, flavor="lattice")
        if lattice_result:
            for table in lattice_result:
                tables = _extract_tables_from_camelot_tables(
                    [table], table.page, "lattice"
                )
                all_tables.extend(tables)
            logger.info(f"Camelot lattice: found {lattice_result.n} table(s)")
        else:
            logger.info("Camelot lattice: no tables found")
    except Exception as e:
        err_msg = f"Camelot lattice failed: {e}"
        logger.warning(err_msg)
        errors.append(err_msg)

    # Try stream flavor
    try:
        stream_result = camelot.read_pdf(pdf_path, pages=camelot_pages, flavor="stream")
        if stream_result:
            for table in stream_result:
                tables = _extract_tables_from_camelot_tables(
                    [table], table.page, "stream"
                )
                all_tables.extend(tables)
            logger.info(f"Camelot stream: found {stream_result.n} table(s)")
        else:
            logger.info("Camelot stream: no tables found")
    except Exception as e:
        err_msg = f"Camelot stream failed: {e}"
        logger.warning(err_msg)
        errors.append(err_msg)

    # Group tables by page
    page_map: dict[int, list[ExtractedTable]] = {}
    for table in all_tables:
        if table.page_number not in page_map:
            page_map[table.page_number] = []
        page_map[table.page_number].append(table)

    # Build ExtractedPage list
    pages_out: list[ExtractedPage] = []
    for page_num in sorted(page_map.keys()):
        tables = page_map[page_num]
        # Sort by table_index
        tables.sort(key=lambda t: t.table_index)
        # Re-index tables per page
        for idx, table in enumerate(tables):
            table.table_index = idx
        pages_out.append(ExtractedPage(
            page_number=page_num,
            text="",  # Camelot doesn't easily extract full page text; use pdfplumber for text
            tables=tables,
        ))

    # If no tables found, create empty pages for pages that were processed
    if not pages_out:
        # Try to get page count from camelot if possible
        pass

    return ExtractedDocument(
        document_id=doc_id,
        file_name=file_name,
        pages=pages_out,
        source_backend="camelot",
    )


# ------------------------------------------------------------------
# Quality scoring
# ------------------------------------------------------------------

# Keywords that suggest a datasheet parameter table
PARAM_TABLE_KEYWORDS = [
    "parameter", "symbol", "conditions", "condition",
    "min", "typ", "max", "unit",
    "characteristics", "electrical",
    "voltage", "current", "resistance", "capacitance",
    "temperature", "time", "energy", "charge",
]


def score_camelot_table(table: ExtractedTable) -> float:
    """Score a Camelot-extracted table for quality.

    Higher score = more likely to be a real parameter table.

    Scoring rules:
    - accuracy: higher is better (normalized to 0-40 points)
    - whitespace: lower is better (normalized to 0-20 points)
    - Row count: 2-50 rows gets points, outside this range loses points
    - Column count: >=3 cols gets points, <2 cols loses points
    - Keyword matches in header/first few rows: +1 per keyword, up to 40 points
    """
    if not table.rows:
        return 0.0

    score = 0.0

    # Accuracy score: 0-40 points
    if table.accuracy is not None:
        score += min(40.0, table.accuracy)

    # Whitespace score: 0-20 points (lower is better)
    if table.whitespace is not None:
        score += max(0.0, 20.0 - table.whitespace)

    row_count = len(table.rows)
    col_count = len(table.rows[0]) if table.rows[0] else 0

    # Row count score: prefer 2-50 rows
    if 2 <= row_count <= 50:
        score += 15.0
    elif row_count > 50:
        score += 5.0  # Too many rows, might be a full-page table
    else:
        score += 0.0  # row_count < 2

    # Column count score: prefer >=3 cols
    if col_count >= 3:
        score += 15.0
    elif col_count == 2:
        score += 5.0
    else:
        score += 0.0

    # Keyword matching in header rows (first 3 rows)
    header_text = ""
    for row in table.rows[:3]:
        header_text += " ".join(row).lower() + " "

    keyword_hits = 0
    for kw in PARAM_TABLE_KEYWORDS:
        if kw.lower() in header_text:
            keyword_hits += 1

    score += min(40.0, keyword_hits * 5.0)

    return round(score, 2)
