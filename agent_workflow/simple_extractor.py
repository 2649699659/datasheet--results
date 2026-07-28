"""
simple_extractor.py — Simplified end-to-end datasheet extraction

A minimal 2-step pipeline:
    Step 0: Camelot table extraction (reuse existing)
    Step 1: Single LLM call to extract all parameters
    Step 2: Excel output

Design goals:
- No complex enrichment phases
- No fixed field list - LLM decides what's important
- Single LLM call for everything
- Maintenance-free (only prompt needs updating)

Usage:
    python3 -m agent_workflow.simple_extractor --pdf path/to/datasheet.pdf --output output_dir/
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from datetime import datetime

# Load .env
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Prompt
# ─────────────────────────────────────────────────────────────────────────────

SIMPLE_EXTRACTOR_PROMPT = """You are a power semiconductor module datasheet extraction expert.

Extract ALL technical specifications from the provided datasheet tables.

## Output Format
Return ONLY valid JSON (no markdown, no explanation). The JSON must have exactly these top-level keys: "metadata" and "parameters".

{{
  "metadata": {{
    "manufacturer": "...",
    "part_number": "...",
    "module_type": "...",
    "description": "..."
  }},
  "parameters": [
    {{
      "name": "...",
      "symbol": "...",
      "value": "...",
      "min": "...",
      "typ": "...",
      "max": "...",
      "unit": "...",
      "condition": "...",
      "source_page": N,
      "source_table": N,
      "source_row": N
    }}
  ]
}}

## Rules

1. Extract ALL parameters you can identify, including but not limited to:
   - Voltage ratings (VDS, VGS, VCES, VRRM, etc.)
   - Current ratings (ID, IC, IFSM, etc.)
   - Resistance values (RDS(on), Ron, etc.)
   - Capacitance values (Ciss, Coss, Crss, etc.)
   - Gate charge (QG, QGS, QGD, etc.)
   - Switching times (td(on), tr, td(off), tf, trr, etc.)
   - Energy values (Eon, Eoff, Ets, etc.)
   - Thermal parameters (RthJC, RthCS, Tj, Tstg, etc.)
   - Mechanical dimensions (length, width, height, etc.)
   - Mounting torque, clearance, creepage

2. For each parameter, identify:
   - name: Full parameter name in English
   - symbol: Standard symbol (e.g., RDS(on), VGS(th), QG)
   - value/min/typ/max: Extract numeric values from the table
   - unit: Physical unit (V, A, mΩ, nC, °C, etc.)
   - condition: Test conditions (e.g., "VGS=18V; ID=150A; TC=25°C")

3. Source location:
   - source_page: Page number where parameter was found
   - source_table: Table index on that page
   - source_row: Row index in the table (0-indexed)

4. If a value is missing, use null (not the string "null")

5. For value ranges like "2-4" or "min/typ/max", extract as separate min/typ/max fields

6. conditions should be normalized:
   - VGS=-5/+18V (not VGS=-5V or VGS=+18V)
   - TC=25°C or TJ=25°C
   - ID=300A, VDD=1200V, VR=600V

7. For module_type, identify from the part number or description:
   - "Half-Bridge", "Sixpack", "PIM", "Chopper", etc.
   - SiC MOSFET, IGBT, etc.

8. manufacturer: Look for company name in header/footer

9. part_number: Usually in a table with "Order Number" or "Type" column

## Datasheet Tables

The following tables were extracted from the PDF using Camelot (showing first 15 rows per table):

{TABLES}

## Now extract all parameters

Return ONLY valid JSON:
"""


def _format_tables_for_prompt(payload_dict: dict, max_rows_per_table: int = 30) -> str:
    """Format CamelotPayload tables for LLM prompt."""
    table_texts = []
    
    for page in payload_dict.get("pages", []):
        page_num = page.get("page_number", "?")
        
        for table in page.get("tables", []):
            table_idx = table.get("table_index", 0)
            flavor = table.get("flavor", "?")
            
            rows = table.get("rows", [])
            if not rows:
                continue
            
            # Format as markdown table (limit rows to avoid token overflow)
            lines = []
            lines.append(f"\n### Page {page_num}, Table {table_idx} ({flavor})\n")
            
            # Header row
            header_cells = rows[0].get("cells", [])
            lines.append("| " + " | ".join(header_cells) + " |")
            lines.append("|" + "|".join(["---"] * len(header_cells)) + "|")
            
            # Data rows (limited)
            for i, row in enumerate(rows[1:max_rows_per_table], start=1):
                cells = row.get("cells", [])
                lines.append("| " + " | ".join(cells) + " |")
            
            if len(rows) > max_rows_per_table:
                lines.append(f"... ({len(rows) - max_rows_per_table} more rows)")
            
            table_texts.append("\n".join(lines))
    
    return "\n\n".join(table_texts)


# ─────────────────────────────────────────────────────────────────────────────
# LLM Call
# ─────────────────────────────────────────────────────────────────────────────

def _call_llm(prompt: str, output_path: Path = None, model: str = None) -> dict:
    """Call LLM API with prompt and return parsed JSON response."""
    import os
    
    # Check cache
    if output_path and output_path.exists():
        logger.info(f"Reading cached LLM response from {output_path}")
        return json.loads(output_path.read_text(encoding="utf-8"))
    
    # API configuration (matching existing step1/step2 approach)
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        raise RuntimeError("No API key found in environment (OPENAI_API_KEY or MINIMAX_API_KEY)")
    
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.minimaxi.chat/v1")
    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    
    if model is None:
        model = os.environ.get("LLM_MODEL", "MiniMax-M2.7")
    
    # Build request (matching existing approach)
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "top_p": 1,
        "seed": 42,
    }
    
    import urllib.request
    import urllib.error
    
    try:
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=300) as response:
            result = json.loads(response.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"]
            
            # Save response to cache
            if output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(content, encoding="utf-8")
            
            # Parse JSON
            return json.loads(content)
            
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        raise RuntimeError(f"LLM API error {e.code}: {error_body}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse LLM response as JSON: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Excel Output
# ─────────────────────────────────────────────────────────────────────────────

def _write_excel(result: dict, output_xlsx: str):
    """Write extraction result to Excel file."""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill
    except ImportError:
        # Try xlsxwriter as fallback
        _write_excel_xlsxwriter(result, output_xlsx)
        return
    
    wb = openpyxl.Workbook()
    
    # Metadata sheet
    ws_meta = wb.active
    ws_meta.title = "Metadata"
    
    metadata = result.get("metadata", {})
    for i, (key, value) in enumerate(metadata.items(), start=1):
        ws_meta.cell(row=i, column=1, value=key)
        ws_meta.cell(row=i, column=2, value=value or "")
    
    # Parameters sheet
    ws_params = wb.create_sheet("Parameters")
    
    # Headers
    headers = ["Name", "Symbol", "Value", "Min", "Typ", "Max", "Unit", "Condition", "Page", "Table", "Row"]
    for col, header in enumerate(headers, start=1):
        cell = ws_params.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="CCCCCC")
    
    # Data
    for row_idx, param in enumerate(result.get("parameters", []), start=2):
        ws_params.cell(row=row_idx, column=1, value=param.get("name") or "")
        ws_params.cell(row=row_idx, column=2, value=param.get("symbol") or "")
        ws_params.cell(row=row_idx, column=3, value=param.get("value") or "")
        ws_params.cell(row=row_idx, column=4, value=param.get("min") or "")
        ws_params.cell(row=row_idx, column=5, value=param.get("typ") or "")
        ws_params.cell(row=row_idx, column=6, value=param.get("max") or "")
        ws_params.cell(row=row_idx, column=7, value=param.get("unit") or "")
        ws_params.cell(row=row_idx, column=8, value=param.get("condition") or "")
        ws_params.cell(row=row_idx, column=9, value=param.get("source_page") or "")
        ws_params.cell(row=row_idx, column=10, value=param.get("source_table") or "")
        ws_params.cell(row=row_idx, column=11, value=param.get("source_row") or "")
    
    # Auto-adjust column widths
    for ws in [ws_meta, ws_params]:
        for column in ws.columns:
            max_length = max(len(str(cell.value or "")) for cell in column)
            ws.column_dimensions[column[0].column_letter].width = min(max_length + 2, 50)
    
    wb.save(output_xlsx)
    logger.info(f"Excel saved to: {output_xlsx}")


def _write_excel_xlsxwriter(result: dict, output_xlsx: str):
    """Fallback Excel writer using xlsxwriter."""
    import xlsxwriter
    
    wb = xlsxwriter.Workbook(output_xlsx)
    
    # Metadata sheet
    ws_meta = wb.add_worksheet("Metadata")
    metadata = result.get("metadata", {})
    for i, (key, value) in enumerate(metadata.items()):
        ws_meta.write(i, 0, key)
        ws_meta.write(i, 1, str(value) if value else "")
    
    # Parameters sheet
    ws_params = wb.add_worksheet("Parameters")
    
    # Headers
    headers = ["Name", "Symbol", "Value", "Min", "Typ", "Max", "Unit", "Condition", "Page", "Table", "Row"]
    for col, header in enumerate(headers):
        ws_params.write(0, col, header)
    
    # Data
    for row_idx, param in enumerate(result.get("parameters", []), start=1):
        ws_params.write(row_idx, 0, param.get("name") or "")
        ws_params.write(row_idx, 1, param.get("symbol") or "")
        ws_params.write(row_idx, 2, param.get("value") or "")
        ws_params.write(row_idx, 3, param.get("min") or "")
        ws_params.write(row_idx, 4, param.get("typ") or "")
        ws_params.write(row_idx, 5, param.get("max") or "")
        ws_params.write(row_idx, 6, param.get("unit") or "")
        ws_params.write(row_idx, 7, param.get("condition") or "")
        ws_params.write(row_idx, 8, param.get("source_page") or "")
        ws_params.write(row_idx, 9, param.get("source_table") or "")
        ws_params.write(row_idx, 10, param.get("source_row") or "")
    
    wb.close()
    logger.info(f"Excel saved to: {output_xlsx}")


# ─────────────────────────────────────────────────────────────────────────────
# Main Pipeline
# ─────────────────────────────────────────────────────────────────────────────

def run_simple_extraction(
    pdf_path: str,
    output_dir: str,
    model: str = None,
    use_cache: bool = True,
) -> dict:
    """
    Run the simplified extraction pipeline.
    
    Steps:
        0. Extract tables with Camelot
        1. Single LLM call to extract all parameters
        2. Write Excel output
    
    Args:
        pdf_path: Path to input PDF
        output_dir: Output directory
        model: Optional LLM model override
        use_cache: Whether to use cached LLM responses
    
    Returns:
        dict with extraction results
    """
    start_time = time.time()
    pdf_stem = Path(pdf_path).stem
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 60)
    logger.info(f"Simple Extractor: {pdf_path}")
    logger.info(f"Output dir: {output_dir}")
    logger.info("=" * 60)
    
    # ── Step 0: Camelot Extraction ──────────────────────────────────────────
    logger.info("Step 0: Extracting tables...")
    
    try:
        from .steps.step0_build_camelot_payload import run as step0_run
        from .artifacts import ArtifactPaths
        
        ap = ArtifactPaths(output_dir, pdf_stem).ensure_dirs()
        camelot_payload = step0_run(pdf_path, ap)
        payload_dict = camelot_payload.to_dict()
        
        table_count = sum(len(p.tables) for p in camelot_payload.pages)
        row_count = sum(len(t.rows) for p in camelot_payload.pages for t in p.tables)
        logger.info(f"Step 0: Extracted {table_count} tables, {row_count} rows")
        
    except Exception as e:
        logger.error(f"Step 0 failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "failed",
            "error": f"Step 0 (Camelot extraction) failed: {e}",
            "elapsed_seconds": time.time() - start_time,
        }
    
    # ── Step 1: LLM Extraction ─────────────────────────────────────────────
    logger.info("Step 1: Extracting parameters with LLM...")
    
    # Cache path for LLM response
    cache_path = output_dir / f"{pdf_stem}_llm_response.json" if use_cache else None
    
    try:
        # Format tables for prompt
        tables_text = _format_tables_for_prompt(payload_dict)
        
        # Build prompt
        prompt = SIMPLE_EXTRACTOR_PROMPT.format(TABLES=tables_text)
        
        # Call LLM
        result = _call_llm(prompt, output_path=cache_path, model=model)
        
        param_count = len(result.get("parameters", []))
        logger.info(f"Step 1: Extracted {param_count} parameters")
        
    except Exception as e:
        logger.error(f"Step 1 failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "failed",
            "error": f"Step 1 (LLM extraction) failed: {e}",
            "elapsed_seconds": time.time() - start_time,
        }
    
    # ── Step 2: Excel Output ────────────────────────────────────────────────
    logger.info("Step 2: Writing Excel...")
    
    output_xlsx = output_dir / f"{pdf_stem}_extracted.xlsx"
    
    try:
        _write_excel(result, str(output_xlsx))
    except Exception as e:
        logger.error(f"Step 2 (Excel) failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "partial",
            "error": f"Excel writing failed: {e}",
            "result": result,
            "elapsed_seconds": time.time() - start_time,
        }
    
    # ── Save JSON ──────────────────────────────────────────────────────────
    output_json = output_dir / f"{pdf_stem}_extracted.json"
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    elapsed = time.time() - start_time
    
    logger.info("=" * 60)
    logger.info(f"Extraction complete in {elapsed:.1f}s")
    logger.info(f"Excel: {output_xlsx}")
    logger.info(f"JSON: {output_json}")
    logger.info("=" * 60)
    
    return {
        "status": "success",
        "pdf_path": pdf_path,
        "output_xlsx": str(output_xlsx),
        "output_json": str(output_json),
        "table_count": table_count,
        "row_count": row_count,
        "parameter_count": len(result.get("parameters", [])),
        "elapsed_seconds": elapsed,
        "result": result,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Simple datasheet extractor")
    parser.add_argument("--pdf", "-p", required=True, help="Input PDF path")
    parser.add_argument("--output", "-o", required=True, help="Output directory")
    parser.add_argument("--model", "-m", help="LLM model override")
    parser.add_argument("--no-cache", action="store_true", help="Disable cache for LLM responses")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s"
    )
    
    result = run_simple_extraction(
        args.pdf, 
        args.output, 
        model=args.model,
        use_cache=not args.no_cache,
    )
    
    if result.get("status") == "failed":
        sys.exit(1)


if __name__ == "__main__":
    main()
