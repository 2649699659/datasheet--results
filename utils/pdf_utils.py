"""
PDF Low-Level Utilities

Uses:
    - pdfplumber for text and table extraction
    - pypdf for metadata

Does NOT use:
    - camelot
    - tabula
    - OCR
    - pytesseract
    - pdf2image
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any

import pypdf
import pdfplumber

from utils.table_normalizer import normalize_tables


def get_pdf_metadata(pdf_path: str) -> Dict[str, Any]:
    """
    Extract basic metadata from PDF using pypdf.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Dict with title, author, page_count
    """
    try:
        with open(pdf_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            metadata = reader.metadata
            
            return {
                "title": metadata.get("/Title", "") if metadata else "",
                "author": metadata.get("/Author", "") if metadata else "",
                "page_count": len(reader.pages),
            }
    except Exception as e:
        return {
            "title": "",
            "author": "",
            "page_count": 0,
            "error": str(e),
        }


def extract_page_text(page: pdfplumber.pdf.Page) -> str:
    """
    Extract text from a single pdfplumber page.
    
    Args:
        page: pdfplumber page object
        
    Returns:
        Extracted text as string
    """
    try:
        return page.extract_text() or ""
    except Exception:
        return ""


def extract_page_raw_tables(page: pdfplumber.pdf.Page) -> List[List[List[str]]]:
    """
    Extract RAW tables from a single pdfplumber page WITHOUT normalization.
    Returns tables as-is from pdfplumber.
    
    Returns:
        List of tables, where each table is a list of rows,
        and each row is a list of cell strings.
    """
    try:
        tables = page.extract_tables()
        return tables or []
    except Exception:
        return []


def extract_all_pages(pdf_path: str) -> Dict[str, Any]:
    """
    Extract all pages from a PDF using pdfplumber.
    Returns both raw and normalized tables.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Dict with pages (raw + normalized), metadata, and file info
    """
    pdf_path = str(Path(pdf_path).resolve())
    file_name = Path(pdf_path).name
    
    # Get metadata with pypdf
    metadata = get_pdf_metadata(pdf_path)
    
    pages = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                # Extract text
                text = extract_page_text(page)
                
                # Extract RAW tables (before normalization)
                raw_tables = extract_page_raw_tables(page)
                
                # Check for low text
                scanned_or_low_text = len(text.strip()) < 50 if text else True
                
                pages.append({
                    "page_number": page_num,
                    "text": text,
                    "raw_tables": raw_tables,
                    "scanned_or_low_text": scanned_or_low_text,
                })
    except Exception as e:
        return {
            "pdf_path": pdf_path,
            "file_name": file_name,
            "metadata": metadata,
            "error": str(e),
            "pages": [],
        }
    
    return {
        "pdf_path": pdf_path,
        "file_name": file_name,
        "metadata": metadata,
        "pages": pages,
    }


def get_page_count(pdf_path: str) -> int:
    """Get page count for a PDF file."""
    metadata = get_pdf_metadata(pdf_path)
    return metadata.get("page_count", 0)
