#!/usr/bin/env python3
"""Backend comparison experiment: Camelot vs pdfplumber table extraction.

Usage:
    python3 experiments/backend_compare.py \\
        --pdf tests/sample_datasheets/ASC300N1200ME3.pdf \\
        --out output/backend_compare
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from extractors.camelot_backend import (
    extract_with_camelot,
    score_camelot_table,
    CAMELOT_AVAILABLE,
)
from extractors.pdfplumber_backend import extract_with_pdfplumber


def preview_table(rows: list[list[str]], max_rows: int = 5) -> list[list[str]]:
    """Return first max_rows rows for preview."""
    return rows[:max_rows]


def build_report(doc_camelot, doc_pdfplumber) -> str:
    """Build markdown comparison report."""
    lines = []
    lines.append("# Backend Comparison Report\n")
    lines.append(f"**PDF**: {doc_camelot.file_name}\n\n")

    # Camelot status
    lines.append("## Camelot Availability\n")
    lines.append(f"- Camelot available: **{'Yes' if CAMELOT_AVAILABLE else 'No'}**\n\n")

    # Camelot lattice vs stream
    camelot_lattice = [t for t in get_all_tables(doc_camelot) if t.flavor == "lattice"]
    camelot_stream = [t for t in get_all_tables(doc_camelot) if t.flavor == "stream"]
    lines.append(f"- Lattice tables: **{len(camelot_lattice)}**\n")
    lines.append(f"- Stream tables: **{len(camelot_stream)}**\n\n")

    # pdfplumber
    pdfplumber_tables = get_all_tables(doc_pdfplumber)
    lines.append(f"## pdfplumber\n")
    lines.append(f"- Total tables: **{len(pdfplumber_tables)}**\n\n")

    # All Camelot tables detail
    all_tables = get_all_tables(doc_camelot)
    lines.append("## Camelot Table Details\n")
    lines.append("| # | Page | Flavor | Shape | Accuracy | Whitespace | Score | Preview |\n")
    lines.append("|---|------|--------|-------|----------|------------|-------|--------|\n")

    for i, table in enumerate(all_tables):
        shape = f"{len(table.rows)}x{len(table.rows[0]) if table.rows else 0}"
        acc = f"{table.accuracy:.1f}" if table.accuracy is not None else "N/A"
        ws = f"{table.whitespace:.1f}" if table.whitespace is not None else "N/A"
        score = f"{score_camelot_table(table):.1f}"
        preview = preview_table(table.rows, 2)
        preview_str = "<br>".join(" | ".join(c[:20] for c in row) for row in preview)
        lines.append(f"| {i} | {table.page_number} | {table.flavor} | {shape} | {acc} | {ws} | {score} | {preview_str} |\n")

    lines.append("\n## Likely Parameter Tables\n")
    scored = [(t, score_camelot_table(t)) for t in all_tables]
    scored.sort(key=lambda x: -x[1])
    likely = [t for t, s in scored if s >= 50]
    lines.append(f"Candidate tables (score >= 50): **{len(likely)}**\n\n")
    for i, table in enumerate(likely):
        shape = f"{len(table.rows)}x{len(table.rows[0]) if table.rows else 0}"
        score = score_camelot_table(table)
        lines.append(f"### Table {i+1} (score={score:.1f})\n")
        lines.append(f"- Page: {table.page_number}, Flavor: {table.flavor}\n")
        lines.append(f"- Shape: {shape}\n")
        lines.append(f"- Accuracy: {table.accuracy}, Whitespace: {table.whitespace}\n")
        lines.append("\n**Preview (first 5 rows):**\n\n")
        lines.append("```\n")
        for row in preview_table(table.rows, 5):
            lines.append("| " + " | ".join(row) + " |\n")
        lines.append("```\n\n")

    lines.append("## Manual Inspection Needed\n")
    uncertain = [t for t, s in scored if 30 <= s < 50]
    lines.append(f"Tables needing review (30 <= score < 50): **{len(uncertain)}**\n\n")
    for i, table in enumerate(uncertain):
        lines.append(f"- Page {table.page_number}, {table.flavor}, score={score_camelot_table(table):.1f}\n")

    # pdfplumber comparison
    lines.append("\n## pdfplumber Tables\n")
    for i, table in enumerate(pdfplumber_tables):
        shape = f"{len(table.rows)}x{len(table.rows[0]) if table.rows else 0}"
        lines.append(f"### Table {i+1}\n")
        lines.append(f"- Page: {table.page_number}, Shape: {shape}\n")
        lines.append("\n**Preview (first 5 rows):**\n\n")
        lines.append("```\n")
        for row in preview_table(table.rows, 5):
            lines.append("| " + " | ".join(row) + " |\n")
        lines.append("```\n\n")

    lines.append("## Recommendations\n")
    if likely:
        lines.append(f"- **{len(likely)} table(s)** scored high enough to likely be parameter tables.\n")
        lines.append("- Camelot is recommended for text-based PDFs; try `--backend camelot`.\n")
    else:
        lines.append("- No tables scored >= 50. Manual inspection required.\n")
    lines.append(f"- Lattice found {len(camelot_lattice)} table(s), stream found {len(camelot_stream)} table(s).\n")
    if len(camelot_lattice) < len(camelot_stream):
        lines.append("- Stream flavor performed better for this PDF.\n")
    elif len(camelot_stream) < len(camelot_lattice):
        lines.append("- Lattice flavor performed better for this PDF.\n")
    else:
        lines.append("- Both flavors found the same number of tables.\n")

    return "".join(lines)


def get_all_tables(doc):
    """Get all tables from an ExtractedDocument."""
    tables = []
    for page in doc.pages:
        tables.extend(page.tables)
    return tables


def main():
    parser = argparse.ArgumentParser(description="Compare table extraction backends")
    parser.add_argument("--pdf", required=True, help="Path to PDF file")
    parser.add_argument("--out", required=True, help="Output directory")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = args.pdf
    print(f"Comparing backends for: {pdf_path}")

    # Extract with Camelot
    print("Extracting with Camelot...")
    doc_camelot = extract_with_camelot(pdf_path)

    # Extract with pdfplumber
    print("Extracting with pdfplumber...")
    doc_pdfplumber = extract_with_pdfplumber(pdf_path)

    # Save JSON
    json_path = out_dir / "camelot_tables.json"
    json_data = {
        "camelot_available": CAMELOT_AVAILABLE,
        "file_name": doc_camelot.file_name,
        "document_id": doc_camelot.document_id,
        "tables": [
            {
                "page_number": t.page_number,
                "table_index": t.table_index,
                "flavor": t.flavor,
                "accuracy": t.accuracy,
                "whitespace": t.whitespace,
                "score": score_camelot_table(t),
                "shape": f"{len(t.rows)}x{len(t.rows[0]) if t.rows else 0}",
                "rows": t.rows,
            }
            for t in get_all_tables(doc_camelot)
        ],
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    print(f"JSON saved: {json_path}")

    # Build and save report
    print("Building report...")
    report = build_report(doc_camelot, doc_pdfplumber)
    report_path = out_dir / "backend_compare.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Report saved: {report_path}")

    # Print summary
    all_camelot = get_all_tables(doc_camelot)
    lattice = [t for t in all_camelot if t.flavor == "lattice"]
    stream = [t for t in all_camelot if t.flavor == "stream"]
    pdf_tables = get_all_tables(doc_pdfplumber)

    print("\n=== Summary ===")
    print(f"Camelot available: {CAMELOT_AVAILABLE}")
    print(f"Camelot lattice: {len(lattice)} tables")
    print(f"Camelot stream: {len(stream)} tables")
    print(f"pdfplumber: {len(pdf_tables)} tables")

    if all_camelot:
        scored = sorted(all_camelot, key=lambda t: -score_camelot_table(t))
        print(f"\nTop 3 Camelot tables by score:")
        for i, t in enumerate(scored[:3]):
            print(f"  {i+1}. page={t.page_number} {t.flavor} score={score_camelot_table(t):.1f} shape={len(t.rows)}x{len(t.rows[0]) if t.rows else 0}")


if __name__ == "__main__":
    main()
