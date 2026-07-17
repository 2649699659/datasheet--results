"""
step0_build_camelot_payload.py — Step 0: Extract PDF with Camelot

Extracts tables from the input PDF using Camelot (both lattice and stream flavors),
then builds a CamelotPayload contract.

Input:  PDF file path
Output: CamelotPayload contract (JSON file)
"""

import hashlib
import logging
from pathlib import Path

from ..contracts import CamelotPayload, CamelotPage, CamelotTable, CamelotTableRow
from ..artifacts import ArtifactPaths, save_payload

logger = logging.getLogger(__name__)

# Camelot is optional
try:
    import camelot
    CAMELOT_AVAILABLE = True
except ImportError:
    CAMELOT_AVAILABLE = False
    camelot = None


def _make_doc_id(pdf_path: str) -> str:
    return hashlib.md5(pdf_path.encode("utf-8")).hexdigest()[:12]


def _clean_cell(text: str) -> str:
    """Clean a single cell text."""
    if not text:
        return ""
    import re
    text = text.replace("\n", " ").replace("\r", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_tables_from_camelot(
    pdf_path: str,
    pages: str = "all",
) -> list[CamelotTable]:
    """Extract tables using both lattice and stream flavors."""
    if not CAMELOT_AVAILABLE:
        raise RuntimeError("Camelot is not available. Install: pip install camelot-py")

    all_tables: list[CamelotTable] = []
    errors: list[str] = []

    for flavor in ["lattice", "stream"]:
        try:
            result = camelot.read_pdf(pdf_path, pages=pages, flavor=flavor)
            if not result:
                continue

            for camelot_table in result:
                if camelot_table.df is None or camelot_table.df.empty:
                    continue

                report = camelot_table.parsing_report
                accuracy = report.get("accuracy")
                whitespace = report.get("whitespace", 0.0)

                rows: list[CamelotTableRow] = []
                for ri, (_, row) in enumerate(camelot_table.df.iterrows()):
                    cells = [
                        _clean_cell(str(cell)) if cell is not None else ""
                        for cell in row
                    ]
                    rows.append(CamelotTableRow(row_index=ri, cells=cells))

                # Score
                score = _score_table(rows, accuracy, whitespace)

                all_tables.append(CamelotTable(
                    page_number=camelot_table.page,
                    table_index=0,  # Will be re-indexed per page
                    flavor=flavor,
                    rows=rows,
                    accuracy=accuracy,
                    whitespace=whitespace,
                    score=score,
                ))

            logger.info(f"Camelot {flavor}: found {result.n} table(s)")
        except Exception as e:
            err_msg = f"Camelot {flavor} failed: {e}"
            logger.warning(err_msg)
            errors.append(err_msg)

    return all_tables


def _score_table(rows: list[CamelotTableRow], accuracy: float | None, whitespace: float | None) -> float:
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
    col_count = len(rows[0].cells) if rows else 0

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
    header_text = " ".join(
        cell for row in rows[:3] for cell in row.cells
    ).lower()

    hits = sum(1 for kw in keywords if kw in header_text)
    score += min(40.0, hits * 5.0)

    return round(score, 2)


def run(pdf_path: str, artifact_paths: ArtifactPaths) -> CamelotPayload:
    """
    Extract tables from PDF and build CamelotPayload.

    Args:
        pdf_path: Path to input PDF
        artifact_paths: Artifact paths manager

    Returns:
        CamelotPayload
    """
    logger.info(f"Step 0: Extracting tables from {pdf_path}")

    pdf_path = str(Path(pdf_path).resolve())
    doc_id = _make_doc_id(pdf_path)
    file_name = Path(pdf_path).name

    # Extract tables
    all_tables = _extract_tables_from_camelot(pdf_path, pages="all")

    # Group by page
    page_map: dict[int, list[CamelotTable]] = {}
    for table in all_tables:
        if table.page_number not in page_map:
            page_map[table.page_number] = []
        page_map[table.page_number].append(table)

    # Sort tables by score descending, re-index per page
    pages_out: list[CamelotPage] = []
    for page_num in sorted(page_map.keys()):
        tables = sorted(page_map[page_num], key=lambda t: t.score, reverse=True)
        for idx, table in enumerate(tables):
            table.table_index = idx
        pages_out.append(CamelotPage(page_number=page_num, tables=tables))

    payload = CamelotPayload(
        document_id=doc_id,
        file_name=file_name,
        pdf_path=pdf_path,
        pages=pages_out,
        source_backend="camelot",
    )

    # Save
    save_payload(payload, artifact_paths.step0_payload())
    logger.info(f"Step 0: Saved {len(all_tables)} tables from {len(pages_out)} pages")

    return payload


if __name__ == "__main__":
    import sys
    from pathlib import Path

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 3:
        print("Usage: python3 step0_build_camelot_payload.py <pdf_path> <output_dir>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_dir = Path(sys.argv[2])
    pdf_stem = Path(pdf_path).stem

    ap = ArtifactPaths(output_dir, pdf_stem).ensure_dirs()
    payload = run(pdf_path, ap)
    print(f"\nExtracted {sum(len(p.tables) for p in payload.pages)} tables from {len(payload.pages)} pages")
    print(f"Payload saved to: {ap.step0_payload()}")
