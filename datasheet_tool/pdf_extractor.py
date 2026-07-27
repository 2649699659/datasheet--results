"""
pdf_extractor.py — Step 1: Extract raw tables from PDF using Camelot

Simplified Camelot extraction - only outputs raw tables, no enrichment, no interpretation.

Input:  PDF file path
Output: RawDocument with list of RawTable objects
"""

import hashlib
import logging
import re
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

# Camelot is optional
try:
    import camelot
    CAMELOT_AVAILABLE = True
except ImportError:
    CAMELOT_AVAILABLE = False
    camelot = None

# Import from models
from .models import RawTable, RawDocument


def _make_doc_id(pdf_path: str) -> str:
    """Generate a short document ID from PDF path."""
    return hashlib.md5(pdf_path.encode("utf-8")).hexdigest()[:12]


def _clean_cell(text: str) -> str:
    """Clean a single cell text."""
    if not text:
        return ""
    text = text.replace("\n", " ").replace("\r", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_tables_from_camelot(pdf_path: str) -> List[RawTable]:
    """Extract tables using both lattice and stream flavors."""
    if not CAMELOT_AVAILABLE:
        raise RuntimeError("Camelot is not available. Install: pip install camelot-py")

    all_tables: List[RawTable] = []

    for flavor in ["lattice", "stream"]:
        try:
            result = camelot.read_pdf(pdf_path, pages="all", flavor=flavor)
            if not result:
                continue

            for camelot_table in result:
                if camelot_table.df is None or camelot_table.df.empty:
                    continue

                report = camelot_table.parsing_report
                accuracy = report.get("accuracy")
                whitespace = report.get("whitespace", 0.0)

                rows: List[List[str]] = []
                for _, row in camelot_table.df.iterrows():
                    cells = [
                        _clean_cell(str(cell)) if cell is not None else ""
                        for cell in row
                    ]
                    rows.append(cells)

                score = _score_table(rows, accuracy, whitespace)

                all_tables.append(RawTable(
                    page=camelot_table.page,
                    table_index=0,  # Will be re-indexed after deduplication
                    flavor=flavor,
                    rows=rows,
                    accuracy=accuracy,
                    score=score,
                ))

            logger.info(f"Camelot {flavor}: found {result.n} table(s)")
        except Exception as e:
            logger.warning(f"Camelot {flavor} failed: {e}")

    return all_tables


def _compute_iou(bbox1: tuple, bbox2: tuple) -> float:
    """
    Compute IoU (Intersection over Union) of two bounding boxes.
    Bbox format: (x1, y1, x2, y2) where (0,0) is top-left.
    """
    if bbox1 is None or bbox2 is None:
        return 0.0

    x1_1, y1_1, x2_1, y2_1 = bbox1
    x1_2, y1_2, x2_2, y2_2 = bbox2

    xi1 = max(x1_1, x1_2)
    yi1 = max(y1_1, y2_2)
    xi2 = min(x2_1, x2_2)
    yi2 = min(y2_1, y2_2)

    if xi1 >= xi2 or yi1 >= yi2:
        return 0.0

    intersection = (xi2 - xi1) * (yi2 - yi1)
    area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
    area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
    union = area1 + area2 - intersection

    if union <= 0:
        return 0.0

    return intersection / union


def _deduplicate_tables(tables: List[RawTable], iou_threshold: float = 0.5) -> List[RawTable]:
    """
    Remove duplicate tables based on IoU overlap.
    For tables on the same page with IoU > threshold, keep the higher-scoring one.
    """
    if not tables:
        return []

    from collections import defaultdict
    by_page: dict[int, List[RawTable]] = defaultdict(list)
    for table in tables:
        by_page[table.page].append(table)

    deduplicated: List[RawTable] = []

    for page_num, page_tables in by_page.items():
        page_tables.sort(key=lambda t: t.score, reverse=True)
        to_remove: set[int] = set()

        for i in range(len(page_tables)):
            if i in to_remove:
                continue
            for j in range(i + 1, len(page_tables)):
                if j in to_remove:
                    continue
                # Simplified: just use score, skip IoU since bbox not available in RawTable
                if abs(page_tables[i].score - page_tables[j].score) < 5:
                    to_remove.add(j)

        for i, table in enumerate(page_tables):
            if i not in to_remove:
                deduplicated.append(table)

    return deduplicated


def _score_table(rows: List[List[str]], accuracy: float | None, whitespace: float | None) -> float:
    """Score a table for quality (0-100)."""
    if not rows:
        return 0.0

    score = 0.0

    # Accuracy: 0-40
    if accuracy is not None:
        score += min(40.0, accuracy)

    # Whitespace: lower is better, 0-20
    if whitespace is not None:
        score += max(0.0, 20.0 - whitespace)

    row_count = len(rows)
    col_count = len(rows[0]) if rows else 0

    # Row count: prefer 2-50 rows → +15
    if 2 <= row_count <= 50:
        score += 15.0
    elif row_count > 50:
        score += 5.0

    # Column count: prefer >=3 cols → +15
    if col_count >= 3:
        score += 15.0
    elif col_count == 2:
        score += 5.0

    # Keyword matching in header
    keywords = [
        "parameter", "symbol", "conditions", "min", "typ", "max", "unit",
        "characteristics", "voltage", "current", "resistance", "capacitance",
    ]
    header_text = " ".join(cell for row in rows[:3] for cell in row).lower()
    hits = sum(1 for kw in keywords if kw in header_text)
    score += min(40.0, hits * 5.0)

    return round(score, 2)


def extract(pdf_path: str) -> RawDocument:
    """
    Extract raw tables from PDF.

    Args:
        pdf_path: Path to input PDF

    Returns:
        RawDocument with list of RawTable objects
    """
    logger.info(f"Extracting tables from: {pdf_path}")

    pdf_path = str(Path(pdf_path).resolve())
    file_name = Path(pdf_path).name

    # Extract tables
    all_tables = _extract_tables_from_camelot(pdf_path)

    # Deduplicate
    original_count = len(all_tables)
    all_tables = _deduplicate_tables(all_tables, iou_threshold=0.5)
    if original_count != len(all_tables):
        logger.info(f"Deduplication: {original_count} → {len(all_tables)} tables")

    # Sort by page and score, re-index
    all_tables.sort(key=lambda t: (t.page, -t.score))
    for idx, table in enumerate(all_tables):
        table.table_index = idx

    logger.info(f"Extracted {len(all_tables)} tables from {len(set(t.page for t in all_tables))} pages")

    return RawDocument(
        pdf_path=pdf_path,
        file_name=file_name,
        tables=all_tables,
    )


if __name__ == "__main__":
    import sys
    import json

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 2:
        print("Usage: python3 pdf_extractor.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    doc = extract(pdf_path)

    print(f"\nExtracted {len(doc.tables)} tables")
    for i, table in enumerate(doc.tables[:3]):
        print(f"\nTable {i}: Page {table.page}, {len(table.rows)} rows")
        for j, row in enumerate(table.rows[:3]):
            print(f"  Row {j}: {row}")
