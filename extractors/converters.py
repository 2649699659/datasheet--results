"""Convert between different extraction formats.

This module converts the unified ExtractedDocument format
to the legacy pipeline format expected by pipeline/extractor.py.
"""

import hashlib
from pathlib import Path

from extractors.base import ExtractedDocument


def extracted_document_to_pipeline_format(
    doc: ExtractedDocument,
    pdf_path: str,
) -> dict:
    """Convert an ExtractedDocument to the legacy pipeline format.

    The legacy pipeline format (from pipeline/extractor.py) is:
    {
        "pdf_path": "...",
        "file_name": "...",
        "metadata": {...},
        "pages": [
            {
                "page_number": 1,
                "text": "...",
                "tables": [
                    {
                        "table_index": 0,
                        "rows": [...],
                        "status": "valid" | "empty_after_normalization"
                    }
                ],
                "scanned_or_low_text": false
            }
        ]
    }

    Args:
        doc: ExtractedDocument from camelot or pdfplumber backend.
        pdf_path: Original PDF file path.

    Returns:
        Dictionary in the legacy pipeline format.
    """
    pdf_path_str = str(pdf_path)
    path_bytes = pdf_path_str.encode("utf-8")
    doc_id = hashlib.md5(path_bytes).hexdigest()[:12]
    file_name = Path(pdf_path).name

    pages_out = []
    for page in doc.pages:
        raw_tables_out = []
        for table in page.tables:
            # process_page_tables expects raw_tables to contain just the 2D list of rows
            # It will call normalize_table on each raw_table
            raw_tables_out.append(table.rows)

        pages_out.append({
            "page_number": page.page_number,
            "text": page.text,
            "raw_tables": raw_tables_out,
            "scanned_or_low_text": False,
            # Store camelot metadata at page level for reference
            "_source_backend": doc.source_backend,
        })

    return {
        "pdf_path": pdf_path_str,
        "document_id": doc_id,
        "file_name": file_name,
        "metadata": {},
        "pages": pages_out,
        "_source_backend": doc.source_backend,
    }


def extract_with_backend(pdf_path: str, backend: str = "pdfplumber") -> ExtractedDocument:
    """Extract tables using the specified backend.

    Args:
        pdf_path: Path to PDF file.
        backend: "pdfplumber" or "camelot".

    Returns:
        ExtractedDocument with all pages and tables.
    """
    if backend == "camelot":
        from extractors.camelot_backend import extract_with_camelot
        return extract_with_camelot(pdf_path)
    else:
        from extractors.pdfplumber_backend import extract_with_pdfplumber
        return extract_with_pdfplumber(pdf_path)
