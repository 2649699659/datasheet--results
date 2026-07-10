"""
PDF Extraction Layer

Responsible for extracting raw content from PDF files.
Does NOT perform complex analysis - just extracts and passes through.

Functions:
    - extract_all_pages(pdf_path) -> Dict
    - extract_page(pdf_path, page_num) -> PageContent
    - get_page_text(page) -> str
    - get_page_tables(page) -> List[Table]

Data structures:
    PageContent:
        page_number: int
        text: str
        tables: List[Table]
        file_name: str

Output format:
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
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Any

from utils.pdf_utils import (
    extract_all_pages as pdfplumber_extract_all,
    get_pdf_metadata,
)
from utils.table_normalizer import normalize_table, truncate_table


def generate_document_id(pdf_path: str) -> str:
    """
    Generate a stable document ID based on file metadata.
    Uses absolute path + file size + modified time to create a unique hash.
    
    Args:
        pdf_path: Absolute path to PDF file
        
    Returns:
        SHA256 hash string (first 16 characters for brevity)
    """
    pdf_path = str(Path(pdf_path).resolve())
    
    try:
        stat = Path(pdf_path).stat()
        # Combine path, size, and mtime for stable hash
        hash_input = f"{pdf_path}:{stat.st_size}:{stat.st_mtime}"
    except Exception:
        # Fallback to just path
        hash_input = pdf_path
    
    return hashlib.sha256(hash_input.encode()).hexdigest()[:16]


def is_table_empty(table: List[List[str]]) -> bool:
    """
    Check if a table is effectively empty.
    Empty means: no rows, or all cells are empty/whitespace.
    
    Args:
        table: Normalized table (list of rows)
        
    Returns:
        True if table is empty
    """
    if not table:
        return True
    
    for row in table:
        for cell in row:
            if cell and cell.strip():
                return False
    return True


def extract_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    Extract all content from a single PDF file.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Dict with pdf_path, file_name, metadata, pages
    """
    return pdfplumber_extract_all(pdf_path)


def extract_pdfs_from_directory(input_path: str) -> List[Dict[str, Any]]:
    """
    Extract all PDFs from a directory.
    
    Args:
        input_path: Directory containing PDF files
        
    Returns:
        List of extraction results, one per PDF
    """
    input_path = Path(input_path)
    
    # Find all PDF files
    pdf_files = list(input_path.glob("*.pdf"))
    pdf_files.extend(input_path.glob("*.PDF"))
    
    results = []
    for pdf_path in sorted(pdf_files):
        try:
            result = extract_pdf(str(pdf_path))
            results.append(result)
        except Exception as e:
            results.append({
                "pdf_path": str(pdf_path),
                "file_name": pdf_path.name,
                "error": str(e),
                "pages": [],
            })
    
    return results


def process_page_tables(page_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process raw tables from a page:
    1. Normalize each table
    2. Mark status (valid / empty_after_normalization)
    3. Calculate per-page stats
    
    Args:
        page_data: Page dict with raw_tables
        
    Returns:
        Processed page with tables, stats
    """
    raw_tables = page_data.get("raw_tables", [])
    text_length = len(page_data.get("text", ""))
    
    tables = []
    valid_count = 0
    empty_count = 0
    
    for table_idx, raw_table in enumerate(raw_tables):
        # Normalize table
        normalized = normalize_table(raw_table)
        
        # Check if empty after normalization
        is_empty = is_table_empty(normalized)
        
        # Determine status
        if is_empty:
            status = "empty_after_normalization"
            empty_count += 1
        else:
            status = "valid"
            valid_count += 1
        
        tables.append({
            "table_index": table_idx,
            "rows": normalized,
            "status": status,
        })
    
    # Determine text_fallback_recommended
    # If no valid tables but text is long enough, recommend text fallback
    text_fallback_recommended = (valid_count == 0 and text_length > 300)
    
    return {
        "page_number": page_data["page_number"],
        "text": page_data["text"],
        "tables": tables,
        "scanned_or_low_text": page_data.get("scanned_or_low_text", False),
        # Stats
        "raw_table_count": len(raw_tables),
        "valid_table_count": valid_count,
        "empty_table_count": empty_count,
        "text_fallback_recommended": text_fallback_recommended,
    }


def extract_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    Extract all content from a single PDF file.
    Adds document_id and pdf_stem for multi-PDF isolation.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Dict with document_id, pdf_stem, pdf_path, file_name, metadata, pages
    """
    result = pdfplumber_extract_all(pdf_path)
    
    # Add document_id for multi-PDF isolation
    result["document_id"] = generate_document_id(pdf_path)
    
    # Add pdf_stem (filename without extension)
    result["pdf_stem"] = Path(pdf_path).stem
    
    return result


def create_debug_output(extraction_results: List[Dict[str, Any]], max_text_len: int = 500, max_table_rows: int = 10) -> Dict[str, Any]:
    """
    Create debug JSON output from extraction results.
    
    Args:
        extraction_results: List of extraction results
        max_text_len: Maximum text characters to keep per page
        max_table_rows: Maximum rows per table
        
    Returns:
        Debug output dict ready for JSON serialization
    """
    debug_output = {
        "extraction_count": len(extraction_results),
        "total_pages": 0,
        "total_raw_tables": 0,
        "total_valid_tables": 0,
        "total_empty_tables": 0,
        "low_text_pages": 0,
        "text_fallback_pages": 0,
        "pdfs": [],
    }
    
    for result in extraction_results:
        if "error" in result:
            debug_output["pdfs"].append({
                "pdf_path": result["pdf_path"],
                "file_name": result["file_name"],
                "error": result["error"],
                "page_count": 0,
                "pages": [],
            })
            continue
        
        pdf_info = {
            "pdf_path": result["pdf_path"],
            "file_name": result["file_name"],
            "document_id": result.get("document_id", ""),
            "pdf_stem": result.get("pdf_stem", ""),
            "metadata": result.get("metadata", {}),
            "page_count": len(result.get("pages", [])),
            "pages": [],
        }
        
        for page_data in result.get("pages", []):
            # Process tables (normalize, mark status, calculate stats)
            page = process_page_tables(page_data)
            
            # Truncate text for debug
            text = page.get("text", "")
            truncated_text = text[:max_text_len] if len(text) > max_text_len else text
            
            page_info = {
                "page_number": page["page_number"],
                "text_length": len(text),
                "text_preview": truncated_text,
                "scanned_or_low_text": page["scanned_or_low_text"],
                # Table stats
                "raw_table_count": page["raw_table_count"],
                "valid_table_count": page["valid_table_count"],
                "empty_table_count": page["empty_table_count"],
                "text_fallback_recommended": page["text_fallback_recommended"],
                "tables": [],
            }
            
            # Track stats
            debug_output["total_pages"] += 1
            debug_output["total_raw_tables"] += page["raw_table_count"]
            debug_output["total_valid_tables"] += page["valid_table_count"]
            debug_output["total_empty_tables"] += page["empty_table_count"]
            
            if page.get("scanned_or_low_text", False):
                debug_output["low_text_pages"] += 1
            
            if page.get("text_fallback_recommended", False):
                debug_output["text_fallback_pages"] += 1
            
            # Add table info
            for table in page.get("tables", []):
                truncated_table = truncate_table(table["rows"], max_rows=max_table_rows)
                table_info = {
                    "table_index": table["table_index"],
                    "row_count": len(table["rows"]),
                    "status": table["status"],
                    "preview_rows": truncated_table,
                }
                page_info["tables"].append(table_info)
            
            pdf_info["pages"].append(page_info)
        
        debug_output["pdfs"].append(pdf_info)
    
    return debug_output


def print_summary(extraction_results: List[Dict[str, Any]], debug_output: Dict[str, Any]):
    """
    Print extraction summary to console.
    
    Args:
        extraction_results: Original extraction results
        debug_output: Processed debug output
    """
    print("\n" + "=" * 60)
    print("EXTRACTION SUMMARY")
    print("=" * 60)
    print(f"  Processed PDFs:           {debug_output['extraction_count']}")
    print(f"  Total Pages:             {debug_output['total_pages']}")
    print(f"  Total Raw Tables:         {debug_output['total_raw_tables']}")
    print(f"  Total Valid Tables:       {debug_output['total_valid_tables']}")
    print(f"  Total Empty Tables:       {debug_output['total_empty_tables']}")
    print(f"  Low Text Pages:           {debug_output['low_text_pages']}")
    print(f"  Text Fallback Pages:      {debug_output['text_fallback_pages']}")
    print("=" * 60)
    
    # Print per-PDF summary
    for pdf_info in debug_output.get("pdfs", []):
        if "error" in pdf_info:
            print(f"  [ERROR] {pdf_info['file_name']}: {pdf_info['error']}")
        else:
            low_text = sum(1 for p in pdf_info["pages"] if p.get("scanned_or_low_text", False))
            text_fallback = sum(1 for p in pdf_info["pages"] if p.get("text_fallback_recommended", False))
            raw_t = sum(p['raw_table_count'] for p in pdf_info['pages'])
            valid_t = sum(p['valid_table_count'] for p in pdf_info['pages'])
            print(f"  {pdf_info['file_name']}: {pdf_info['page_count']} pages, {raw_t} raw tables, {valid_t} valid, {text_fallback} text-fallback")
    
    print("=" * 60)
