"""
Generic AI-first table extractor for power module datasheets.

This module provides per-page AI extraction to maximize parameter coverage
for non-ASC modules (e.g., Wolfspeed).

Key principles:
- Per-page extraction (not whole PDF at once)
- Preserve table structure (headers, columns, units) for AI
- Source validation: reject if source_text doesn't match page content
- No value inference or calculation
- No cross-part contamination
"""
import json
import os
import re
from pathlib import Path
from typing import Optional

# Import from existing module
from core.module_extractor import (
    extract_with_pdfplumber,
    call_deepseek_llm,
    DEEPSEEK_API_KEY,
)


def get_page_data(pdfplumber_result: dict, page_num: int) -> Optional[dict]:
    """
    Get data for a specific page from pdfplumber result.
    
    Args:
        pdfplumber_result: Result from extract_with_pdfplumber
        page_num: 1-indexed page number (1 = first page)
    
    Returns:
        Page dict with 'text', 'tables', or None if page not found.
    """
    pages = pdfplumber_result.get("pages", [])
    idx = page_num - 1
    if 0 <= idx < len(pages):
        return pages[idx]
    return None


def _extract_section_from_text(text: str, table_area: str = "") -> str:
    """
    Try to extract section/heading context from page text near the table.
    """
    # Look for common section headings in power module datasheets
    patterns = [
        r"(?:TABLE|Table)\s*\d*[.:]\s*([^\n\[]+)",
        r"(?:MOSFET|Dynamic|Static|Switching|Mechanical|Thermal|Electrical)?\s*(?:Characteristics|Parameters|Ratings|Specifications)[^\n]*",
        r"(?:Absolute Maximum|Recommended Operating|Electrical Characteristics)[^\n]*",
        r"(?:Clearance|Creepage|Isolation|Weight|Dimensions|Mounting)[^\n]*",
    ]
    
    for pat in patterns:
        m = re.search(pat, text[:2000], re.IGNORECASE)
        if m:
            return m.group(0).strip()
    
    return ""


def format_page_tables_markdown(page_data: dict, max_tables: int = 15) -> str:
    """
    Format tables as structured markdown for AI consumption.
    
    Uses simple pipe-delimited rows (proven to work with LLM).
    Also tries to detect and include section context for mechanical tables.
    """
    table_parts = []
    tables = page_data.get("tables", [])[:max_tables]
    page_text = page_data.get("text", "")[:2000]
    
    # Extract section context from page text
    section_context = _extract_section_from_text(page_text)
    
    for i, table in enumerate(tables):
        rows = table.get("data", [])
        if not rows:
            continue
        
        part = []
        
        # Add section context if this looks like a mechanical/insulation table
        # (Section context helps the LLM understand Clearance/Creepage rows)
        if section_context:
            mech_keywords = ["clearance", "creepage", "weight", "isolation", "mounting",
                           "torque", "dimension", "mechanical", "physical"]
            if any(kw in section_context.lower() for kw in mech_keywords):
                part.append(f"Section: {section_context}")
        
        # Format each row as pipe-delimited (simple and reliable)
        for row in rows[:30]:
            if isinstance(row, dict):
                cells = row.get("cells", [])
            elif isinstance(row, list):
                cells = [str(c).strip() if c else "" for c in row]
            else:
                cells = [str(row).strip()]
            
            # Join with pipe, include ALL cells (including empty ones for alignment)
            row_str = " | ".join(cells)
            # Clean up excessive whitespace
            row_str = re.sub(r"\s+", " ", row_str).strip()
            if row_str and row_str != "|":
                part.append(row_str)
        
        if part:
            table_parts.append("\n".join(part))
    
    return "\n\n".join(table_parts)


def format_page_text(page_data: dict) -> str:
    """
    Extract readable text from a single page.
    """
    text_parts = []
    
    if page_data.get("text"):
        text_parts.append(page_data["text"])
    
    return "\n".join(text_parts)


def format_page_tables(page_data: dict, max_tables: int = 15) -> str:
    """
    Format tables from a single page for AI consumption.
    
    Uses simple pipe-delimited rows with section context for mechanical tables.
    """
    return format_page_tables_markdown(page_data, max_tables)


def extract_page_with_ai(
    pdfplumber_result: dict,
    page_num: int,
    part_number: str,
    manufacturer: str,
    cache_dir: Optional[str] = None,
    use_cache: bool = True,
) -> dict:
    """
    Extract parameters from a single page using AI.
    """
    from core.ai.prompts import build_page_extraction_prompt
    
    # Get page data
    page_data = get_page_data(pdfplumber_result, page_num)
    if not page_data:
        return {"page": page_num, "parameters": []}
    
    # Format page content
    page_text = format_page_text(page_data)
    formatted_tables = format_page_tables(page_data)
    
    if not page_text.strip() and not formatted_tables.strip():
        return {"page": page_num, "parameters": []}
    
    # Check cache
    cache_key = f"ai_page_{part_number}_p{page_num}"
    if use_cache and cache_dir:
        cache_path = Path(cache_dir) / f"{cache_key}.json"
        if cache_path.exists():
            try:
                with open(cache_path, encoding="utf-8") as f:
                    cached = json.load(f)
                    print(f"    [AI PAGE CACHE HIT] page {page_num}")
                    return cached
            except (json.JSONDecodeError, IOError):
                pass
    
    # Build prompt
    prompt = build_page_extraction_prompt(
        part_number=part_number,
        manufacturer=manufacturer,
        page_number=page_num,
        page_text=page_text[:3000],
        raw_tables=formatted_tables[:8000],
    )
    
    # Save debug input
    if cache_dir:
        debug_dir = Path(cache_dir).parent / "debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
        debug_file = debug_dir / f"page_{page_num}_llm_input.md"
        debug_content = f"""# LLM Input Debug - Page {page_num}
# Part: {part_number} | Manufacturer: {manufacturer}

## Page Text (truncated)
```
{page_text[:2000]}
```

## Formatted Tables
```
{formatted_tables[:8000]}
```

## Full Prompt Sent to LLM
```
{prompt}
```
"""
        with open(debug_file, "w", encoding="utf-8") as f:
            f.write(debug_content)
        print(f"    [DEBUG] Saved LLM input to {debug_file}")
    
    # Call LLM
    print(f"    [AI PAGE] Calling LLM for page {page_num}...")
    try:
        result = call_deepseek_llm(prompt, DEEPSEEK_API_KEY)
    except Exception as e:
        print(f"    [AI PAGE ERROR] page {page_num}: {e}")
        return {"page": page_num, "parameters": [], "error": str(e)}
    
    # Parse result
    if "error" in result:
        print(f"    [AI PAGE ERROR] page {page_num}: {result['error']}")
        return {"page": page_num, "parameters": [], "error": result["error"]}
    
    if not isinstance(result, dict):
        return {"page": page_num, "parameters": []}
    
    params = result.get("parameters", [])
    
    # Validate and post-process each parameter
    validated_params = []
    for param in params:
        validated = validate_ai_param(param, page_text, formatted_tables)
        if validated:
            validated_params.append(validated)
    
    output = {
        "page": page_num,
        "parameters": validated_params,
    }
    
    # Save to cache
    if use_cache and cache_dir:
        cache_path = Path(cache_dir) / f"{cache_key}.json"
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"    [AI PAGE CACHE SAVE] page {page_num} ({len(validated_params)} params)")
    
    return output


def validate_ai_param(param: dict, page_text: str, formatted_tables: str) -> Optional[dict]:
    """
    Validate that AI-extracted parameter has valid source_text.
    """
    source_text = param.get("source_text", "").strip()
    symbol = param.get("symbol", "")
    
    if not source_text:
        param["status"] = "needs_review"
        param["review_reason"] = "empty_source_text"
        return param
    
    # Check if source_text matches something in the original text
    combined = (page_text + "\n" + formatted_tables).lower()
    source_lower = source_text.lower()
    
    # Extract tokens to check
    tokens = []
    for val_key in ["typ", "min", "max", "value"]:
        val = param.get(val_key, "")
        if val:
            tokens.append(str(val))
    if symbol:
        tokens.append(symbol)
    
    matched = sum(1 for t in tokens if t.lower() in combined)
    
    if matched == 0 and tokens:
        param["status"] = "needs_review"
        param["review_reason"] = "tokens_not_in_source"
        return param
    
    confidence = param.get("confidence", 0.5)
    param["status"] = "confirmed" if (confidence >= 0.5 and matched > 0) else "needs_review"
    
    return param


def extract_all_pages_with_ai(
    pdf_path: str,
    part_number: str,
    manufacturer: str,
    output_dir: Optional[str] = None,
    use_llm: bool = True,
    use_cache: bool = True,
) -> list:
    """
    Extract parameters from all pages using AI.
    """
    print(f"\n[AI EXTRACTION] Starting for {part_number}")
    
    # Run pdfplumber extraction
    print(f"[AI EXTRACTION] Extracting PDF pages...")
    pdfplumber_result = extract_with_pdfplumber(pdf_path)
    
    if pdfplumber_result.get("status") == "error":
        print(f"  ERROR: {pdfplumber_result.get('error')}")
        return []
    
    pages = pdfplumber_result.get("pages", [])
    total_pages = len(pages)
    print(f"  Total pages: {total_pages}")
    
    # Cache directory for AI results
    cache_dir = None
    if output_dir:
        cache_dir = os.path.join(output_dir, ".ai_cache")
    
    # Extract each page
    all_params = []
    page_results = []
    
    for page_num in range(1, total_pages + 1):
        print(f"\n[AI EXTRACTION] Processing page {page_num}/{total_pages}...")
        
        if use_llm:
            page_result = extract_page_with_ai(
                pdfplumber_result=pdfplumber_result,
                page_num=page_num,
                part_number=part_number,
                manufacturer=manufacturer,
                cache_dir=cache_dir,
                use_cache=use_cache,
            )
        else:
            page_result = {"page": page_num, "parameters": [], "note": "llm_disabled"}
        
        page_results.append(page_result)
        
        for param in page_result.get("parameters", []):
            param["extraction_method"] = "llm_page_extract"
            param["extraction_page"] = page_num
            all_params.append(param)
    
    print(f"\n[AI EXTRACTION] Total parameters extracted: {len(all_params)}")
    
    if output_dir:
        results_path = Path(output_dir) / "ai_extraction_results.json"
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump({
                "part_number": part_number,
                "manufacturer": manufacturer,
                "total_pages": total_pages,
                "total_parameters": len(all_params),
                "page_results": page_results,
                "all_parameters": all_params,
            }, f, ensure_ascii=False, indent=2)
        print(f"[AI EXTRACTION] Saved results to {results_path}")
    
    return all_params


def normalize_ai_params(params: list) -> list:
    """
    Normalize AI-extracted parameters to match the all_params format.
    """
    normalized = []
    
    for param in params:
        value = param.get("value") or param.get("typ") or ""
        condition = param.get("condition", "") or ""
        
        status = param.get("status", "confirmed")
        if status == "needs_review":
            review_reason = param.get("review_reason", "")
            status = f"needs_review({review_reason})"
        
        normalized_param = {
            "symbol": param.get("symbol", ""),
            "parameter": param.get("parameter", "") or param.get("symbol", ""),
            "value": value,
            "typ": param.get("typ"),
            "min": param.get("min"),
            "max": param.get("max"),
            "unit": param.get("unit", ""),
            "condition": condition,
            "source_page": param.get("source_page") or param.get("extraction_page", ""),
            "source_text": param.get("source_text", ""),
            "status": status,
            "category": param.get("category", "general"),
            "section": param.get("section", ""),
            "extraction_method": param.get("extraction_method", "llm_page_extract"),
            "confidence": param.get("confidence"),
            "raw_row": param.get("raw_row", ""),
            "table_context": param.get("table_context", {}),
        }
        
        normalized.append(normalized_param)
    
    return normalized


def merge_extractions(
    original_params: list,
    ai_params: list,
    use_ai_priority: bool = True,
) -> list:
    """
    Merge AI-extracted parameters with original extraction results.
    """
    original_map = {}
    for param in original_params:
        symbol = param.get("symbol", "").strip().lower()
        if symbol:
            original_map[symbol] = param
    
    ai_map = {}
    for param in ai_params:
        symbol = param.get("symbol", "").strip().lower()
        if symbol:
            if symbol not in ai_map:
                ai_map[symbol] = []
            ai_map[symbol].append(param)
    
    merged = []
    seen_symbols = set()
    
    for symbol, ai_param_list in ai_map.items():
        best_param = max(ai_param_list, key=lambda p: p.get("confidence", 0))
        
        if symbol in original_map and use_ai_priority:
            original = original_map[symbol]
            if original.get("status") == "confirmed" and best_param.get("status") == "needs_review":
                best_param["status"] = original["status"]
        
        best_param["extraction_method"] = "llm_page_extract"
        merged.append(best_param)
        seen_symbols.add(symbol)
    
    for symbol, original in original_map.items():
        if symbol not in seen_symbols:
            original_copy = original.copy()
            original_copy["extraction_method"] = original_copy.get("extraction_method", "table_rule")
            merged.append(original_copy)
            seen_symbols.add(symbol)
    
    return merged


if __name__ == "__main__":
    import tempfile
    
    pdf_path = "datasheets_module/Wolfspeed_CAB530M12BM3_data_sheet---9136cddf-8d8f-4737-a97b-9b1ecdef641a.pdf"
    
    with tempfile.TemporaryDirectory() as tmpdir:
        params = extract_all_pages_with_ai(
            pdf_path=pdf_path,
            part_number="CAB530M12BM3",
            manufacturer="Wolfspeed",
            output_dir=tmpdir,
            use_llm=True,
            use_cache=False,
        )
        
        normalized = normalize_ai_params(params)
        
        print(f"\nTotal normalized params: {len(normalized)}")
        for p in normalized[:10]:
            print(f"  {p['symbol']}: {p.get('value') or p.get('typ')} {p.get('unit')} - {p['status']}")
