#!/usr/bin/env python3
"""
Minimal AI-first extraction test for Wolfspeed CAB530M12BM3.
Only pages 1-3. No Excel generation. No multi-PDF processing.

This script is used for TESTING ONLY - not part of v1.0-lite or v1.1 production.
"""

import os
import sys
import json
import argparse
import glob
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.module_extractor import extract_with_pdfplumber
from core.ai.generic_table_extractor import format_page_tables, format_page_text, get_page_data
from core.ai.prompts import build_page_extraction_prompt
from core.ai.normalizer import normalize_ai_parameters, extract_stats
from core.ai.text_block_extractor import extract_relevant_text_blocks, format_text_blocks_for_prompt


def call_llm(prompt: str, api_key: str, timeout: int = 60) -> dict:
    """Call DeepSeek LLM API with timeout."""
    import requests
    
    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 8000
    }
    
    response = requests.post(url, headers=headers, json=data, timeout=timeout)
    
    if response.status_code != 200:
        raise Exception(f"LLM API error: {response.status_code} - {response.text}")
    
    result = response.json()
    content = result["choices"][0]["message"]["content"]
    
    # Parse JSON from response
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()
    
    # Validate it looks like complete JSON (check for trailing closure)
    if not content.endswith("}") and not content.endswith("]"):
        # Try to find the last complete object
        last_brace = content.rfind("}")
        last_bracket = content.rfind("]")
        end = max(last_brace, last_bracket)
        if end > 0:
            content = content[:end+1]
    
    return json.loads(content)


def validate_and_fix_param(p: dict, page_text: str, raw_tables: str) -> dict:
    """
    Validate and fix a single extracted parameter.
    
    Validation rules:
    - source_text is empty or null → status = "needs_review"
    - value/typ/min/max all empty/null or "-" → status = "needs_review"  
    - source_text key tokens not in page_text/raw_tables → needs_review
    - Pass all checks → status = "confirmed" (only if LLM said confirmed)
    """
    p = dict(p)  # Don't mutate original
    
    has_value = any([
        p.get('value') and str(p.get('value')).strip() not in ['', '-', '—', 'N/A', 'null', 'None'],
        p.get('typ') and str(p.get('typ')).strip() not in ['', '-', '—', 'N/A', 'null', 'None'],
        p.get('min') and str(p.get('min')).strip() not in ['', '-', '—', 'N/A', 'null', 'None'],
        p.get('max') and str(p.get('max')).strip() not in ['', '-', '—', 'N/A', 'null', 'None'],
    ])
    
    has_source = p.get('source_text') and str(p.get('source_text')).strip() not in ['', '-', '—', 'N/A', 'null', 'None']
    
    if not has_source or not has_value:
        p['status'] = 'needs_review'
        p['review_reason'] = 'empty_source_or_value'
    
    return p


def _extract_params_from_raw_text(prompt: str, api_key: str) -> list:
    """
    Fallback when JSON parsing fails.
    Try to extract parameters using a simpler direct approach.
    """
    import re
    try:
        # Extract the tables portion from the prompt
        tables_match = re.search(r"Formatted Tables\n```\n(.*?)\n```", prompt, re.DOTALL)
        if not tables_match:
            return []
        
        tables_text = tables_match.group(1)
        
        # Build a simpler extraction prompt
        simple_prompt = f"""Extract these power module parameters from the table below. Return ONLY a JSON array with each parameter as {{"symbol": "X", "typ": "Y", "unit": "Z"}}.

Table:
{tables_text[:3000]}

Return JSON only, no markdown."""
        
        response = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": [{"role": "user", "content": simple_prompt}],
                  "temperature": 0.0, "max_tokens": 8000},
            timeout=90
        )
        
        if response.status_code != 200:
            return []
        
        content = response.json()["choices"][0]["message"]["content"].strip()
        content = content.strip("```json").strip("```").strip()
        
        items = json.loads(content)
        if not isinstance(items, list):
            return []
        
        params = []
        for item in items:
            if isinstance(item, dict):
                p = {
                    "symbol": item.get("symbol", ""),
                    "typ": item.get("typ") or item.get("value"),
                    "unit": item.get("unit", ""),
                    "condition": item.get("condition", ""),
                    "status": "needs_review",
                    "confidence": 0.5,
                }
                params.append(p)
        
        return params
    except Exception:
        return []


def extract_page_with_ai(pdf_path: str, page_num: int, part_number: str, 
                         manufacturer: str, output_dir: str = "output/ai_extract") -> list:
    """Extract parameters from a single page using AI with validation."""
    
    print(f"  Processing page {page_num}...")
    
    # Extract page data with pdfplumber
    result = extract_with_pdfplumber(pdf_path)
    page_data = get_page_data(result, page_num)
    
    # Format tables (new markdown format) and page text
    formatted_tables = format_page_tables(page_data)
    page_text = format_page_text(page_data)
    
    # Extract text fallback blocks for page 3 (mechanical/isolation pages)
    # This recovers section headers that pdfplumber table extraction may have lost
    text_blocks_str = ""
    if page_num == 3:
        text_blocks = extract_relevant_text_blocks(page_text, page_num)
        text_blocks_str = format_text_blocks_for_prompt(text_blocks)
        print(f"  [TEXT FALLBACK] Found {len(text_blocks)} text blocks for page {page_num}")
    
    # Build prompt (generic, no manufacturer-specific content)
    prompt = build_page_extraction_prompt(
        part_number=part_number,
        manufacturer=manufacturer,
        page_number=page_num,
        page_text=page_text[:2000],
        raw_tables=formatted_tables[:8000],
        text_blocks=text_blocks_str
    )
    
    # Save debug input file
    debug_dir = os.path.join(output_dir, "debug")
    os.makedirs(debug_dir, exist_ok=True)
    debug_file = os.path.join(debug_dir, f"page_{page_num}_llm_input.md")
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

## Text Fallback Blocks (Page 3 Only)
{text_blocks_str}

## Full Prompt
```
{prompt}
```
"""
    with open(debug_file, "w", encoding="utf-8") as f:
        f.write(debug_content)
    print(f"  [DEBUG] Saved LLM input to {debug_file}")
    
    # Get API key
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("DEEPSEEK_API_KEY="):
                        api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
    
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY not found in environment or .env file")
    
    # Call LLM with timeout
    print(f"  [LLM CALL] Page {page_num}...")
    try:
        llm_result = call_llm(prompt, api_key, timeout=90)
        params = llm_result.get("parameters", [])
        print(f"  [LLM DONE] Page {page_num}: extracted {len(params)} parameters")
    except (json.JSONDecodeError, ValueError) as e:
        print(f"  [LLM JSON ERROR] Page {page_num}: {e}")
        # Try regex fallback to extract parameters from malformed JSON
        params = _extract_params_from_raw_text(prompt, api_key)
        print(f"  [LLM REGEX RECOVERY] Page {page_num}: recovered {len(params)} parameters")
        if not params:
            print(f"  [LLM FALLBACK FAILED] Page {page_num}")
            return []
    
    # Validate and fix each parameter
    validated_params = []
    for p in params:
        p["source_page"] = page_num
        p["extraction_method"] = "llm_page_extract"
        p["raw_row"] = p.get("raw_row", p.get("source_text", ""))
        p["table_context"] = p.get("table_context", {})
        p = validate_and_fix_param(p, page_text, formatted_tables)
        validated_params.append(p)
    
    return validated_params


def find_wolfspeed_pdf(input_dir: str) -> str:
    """Find Wolfspeed or CAB530 PDF in directory."""
    patterns = [
        os.path.join(input_dir, "*Wolfspeed*CAB530*.pdf"),
        os.path.join(input_dir, "*CAB530*.pdf"),
        os.path.join(input_dir, "*Wolfspeed*.pdf"),
        os.path.join(input_dir, "*.pdf"),
    ]
    
    for pattern in patterns:
        files = glob.glob(pattern)
        for f in files:
            name = os.path.basename(f).lower()
            if "wolfspeed" in name or "cab530" in name:
                return f
    
    for pattern in patterns:
        files = glob.glob(pattern)
        if files:
            return files[0]
    
    raise FileNotFoundError(f"No PDF found in {input_dir}")


def main():
    parser = argparse.ArgumentParser(description="Minimal AI extraction test for Wolfspeed CAB530")
    parser.add_argument("--pdf", type=str, help="Path to Wolfspeed PDF (auto-detected if omitted)")
    parser.add_argument("--pages", type=str, default="1-3", help="Page range, e.g. 1-3 or 2,3,4")
    parser.add_argument("--output", type=str, default="output/ai_extract", help="Output directory")
    args = parser.parse_args()
    
    # Find PDF
    if args.pdf:
        pdf_path = args.pdf
    else:
        input_dir = os.path.join(os.path.dirname(__file__), "..", "datasheets_module")
        pdf_path = find_wolfspeed_pdf(input_dir)
    
    print(f"Using PDF: {pdf_path}")
    pdf_name = os.path.basename(pdf_path)
    
    # Parse page range
    page_range = []
    if "-" in args.pages:
        start, end = args.pages.split("-")
        page_range = list(range(int(start), int(end) + 1))
    else:
        page_range = [int(p.strip()) for p in args.pages.split(",")]
    
    print(f"Processing pages: {page_range}")
    
    # Output setup
    output_dir = args.output
    os.makedirs(output_dir, exist_ok=True)
    
    # Clear AI cache to force fresh extraction with new formatter
    cache_dir = os.path.join(output_dir, ".ai_cache")
    if os.path.exists(cache_dir):
        import shutil
        shutil.rmtree(cache_dir)
        print(f"  [CACHE] Cleared cache directory")
    
    # Part number and manufacturer
    part_number = "CAB530M12BM3"
    manufacturer = "Wolfspeed"
    
    # Extract from each page
    all_params = []
    total_llm_calls = 0
    
    for page_num in page_range:
        try:
            params = extract_page_with_ai(
                pdf_path=pdf_path,
                page_num=page_num,
                part_number=part_number,
                manufacturer=manufacturer,
                output_dir=output_dir,
            )
            all_params.extend(params)
            total_llm_calls += 1
        except Exception as e:
            print(f"  [ERROR] Page {page_num}: {e}")
            continue
    
    # Build output JSON (raw)
    output_data = {
        "pdf": pdf_name,
        "part_number": part_number,
        "manufacturer": manufacturer,
        "pages": page_range,
        "parameters": all_params,
        "llm_calls": total_llm_calls,
    }
    
    # Save raw JSON
    output_file = os.path.join(output_dir, f"{part_number}_ai_parameters.json")
    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    # Normalize
    normalized = normalize_ai_parameters(all_params)
    norm_stats = extract_stats(normalized)
    
    # Remove stats from parameters list
    params_only = [p for p in normalized if not (isinstance(p, dict) and "_normalizer_stats" in p)]
    
    # Build normalized output JSON
    normalized_data = {
        "pdf": pdf_name,
        "part_number": part_number,
        "manufacturer": manufacturer,
        "pages": page_range,
        "parameters": params_only,
        "llm_calls": total_llm_calls,
        "normalizer_stats": norm_stats,
    }
    
    # Save normalized JSON
    normalized_file = os.path.join(output_dir, f"{part_number}_ai_parameters_normalized.json")
    with open(normalized_file, "w") as f:
        json.dump(normalized_data, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print("\n" + "="*60)
    print("EXTRACTION SUMMARY")
    print("="*60)
    print(f"LLM calls made: {total_llm_calls}")
    print(f"Raw parameters: {len(all_params)}")
    print(f"Normalized parameters: {len(params_only)}")
    print(f"Raw JSON: {output_file}")
    print(f"Normalized JSON: {normalized_file}")
    print("="*60)
    
    # Per-page breakdown (normalized)
    for page_num in page_range:
        page_params = [p for p in params_only if p.get("source_page") == page_num]
        print(f"  Page {page_num}: {len(page_params)} parameters")
    
    # Status breakdown (normalized)
    confirmed = [p for p in params_only if p.get("status") == "confirmed"]
    needs_review = [p for p in params_only if p.get("status") == "needs_review"]
    needs_alias = [p for p in params_only if p.get("status") == "needs_alias_review"]
    print(f"\nStatus breakdown (normalized):")
    print(f"  confirmed: {len(confirmed)}")
    print(f"  needs_review: {len(needs_review)}")
    print(f"  needs_alias_review: {len(needs_alias)}")
    
    # Normalizer stats
    print(f"\nNormalizer stats:")
    print(f"  unit fixed: {norm_stats.get('unit_fixed', 0)}")
    print(f"  symbol alias fixed: {norm_stats.get('symbol_alias_fixed', 0)}")
    print(f"  symbol inferred: {norm_stats.get('symbol_inferred', 0)}")
    print(f"  condition fixed: {norm_stats.get('condition_fixed', 0)}")
    print(f"  value_to_typ fixed: {norm_stats.get('value_to_typ', 0)}")
    
    # Preview first 30 parameters (normalized)
    print("\nFIRST 30 NORMALIZED PARAMETERS PREVIEW:")
    print("-"*80)
    for i, p in enumerate(params_only[:30]):
        sym = p.get("symbol", "-") or "-"
        val = str(p.get("typ") or p.get("value") or p.get("min") or "-")
        unit = p.get("unit", "") or ""
        page = p.get("source_page", "?")
        status = p.get("status", "?")
        cond = (p.get("condition") or "")[:40]
        marker = " ⚠️" if status != "confirmed" else ""
        print(f"  {i+1:2d}. [P{page}] {sym:20s}: {val:12s} {unit:6s}{marker} [{status}]")
        if cond:
            print(f"       cond: {cond}")
    
    return normalized_data


if __name__ == "__main__":
    main()
