"""Table extraction backends for datasheet extraction."""

from extractors.base import ExtractedTable, ExtractedPage, ExtractedDocument
from extractors.pdfplumber_backend import extract_with_pdfplumber
from extractors.camelot_backend import extract_with_camelot, score_camelot_table
from extractors.converters import (
    extracted_document_to_pipeline_format,
    extract_with_backend,
)

__all__ = [
    "ExtractedTable",
    "ExtractedPage",
    "ExtractedDocument",
    "extract_with_pdfplumber",
    "extract_with_camelot",
    "score_camelot_table",
    "extracted_document_to_pipeline_format",
    "extract_with_backend",
]
