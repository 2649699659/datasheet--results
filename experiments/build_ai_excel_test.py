#!/usr/bin/env python3
"""
Build AI-enhanced Excel from v1.0-lite base + AI normalized JSON.

Usage:
    python3 experiments/build_ai_excel_test.py \
        --base-excel output/datasheet_extractor_lite.xlsx \
        --ai-json output/ai_extract/CAB530M12BM3_ai_parameters_normalized.json \
        --output output/datasheet_extractor_lite_ai.xlsx
"""
import argparse
import json
import os
import re
import shutil
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
sys.path.insert(0, PROJECT_ROOT)

from core.ai.merge_ai_parameters import (
    merge_parameters,
    build_ai_parameters_sheet_data,
    build_ai_evaluation_sheet_data,
)


def normalize_key(s: str) -> str:
    """Normalize a string for comparison."""
    if not s:
        return ""
    return re.sub(r"[^a-zA-Z0-9]", "", s).lower()


def load_all_params_as_tuples(ws) -> list[list]:
    """
    Load All Parameters sheet as list of lists.
    Returns (headers, rows) where headers are title-case.
    """
    headers = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
    rows = []
    for r in range(2, ws.max_row + 1):
        row = [ws.cell(r, c).value for c in range(1, ws.max_column + 1)]
        rows.append(row)
    return headers, rows


def _is_empty(v) -> bool:
    """Check if a value is empty."""
    if v is None:
        return True
    if isinstance(v, str) and v.strip() in ("", "-", "-", "N/A", "None", "UNKNOWN"):
        return True
    return False


def str_val(v) -> str:
    """Convert a value to string for Excel."""
    if v is None:
        return ""
    if isinstance(v, list):
        return "; ".join(str(x) for x in v)
    return str(v)


def _normalize_row_dict(row_data: dict) -> dict:
    """
    Normalize a row dict to use lowercase keys for the original headers.
    This fixes the mixed-case key issue where merged data has both 'Value' and 'value'.
    """
    normalized = {}
    # First copy all existing keys (lowercase them for consistent lookup)
    for k, v in row_data.items():
        normalized[k.lower()] = v
    return normalized


def write_all_params_enhanced(ws, headers: list, rows_data: list[dict], extra_cols: list[str]):
    """
    Write enhanced All Parameters with extra AI columns.
    
    Args:
        ws: worksheet
        headers: original v1.0-lite headers (title case)
        rows_data: list of dicts (merged rows with mixed case keys)
        extra_cols: additional AI columns to add at the end
    """
    all_headers = list(headers) + list(extra_cols)
    n_orig = len(headers)
    
    # Write header row
    header_fill = PatternFill("solid", fgColor="4472C4")
    header_font = Font(bold=True, color="FFFFFF")
    for c, h in enumerate(all_headers, 1):
        cell = ws.cell(1, c)
        cell.value = h
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", wrap_text=True)
    
    # Write data rows
    ai_status_fill_confirmed = PatternFill("solid", fgColor="C6EFCE")
    ai_status_fill_alias = PatternFill("solid", fgColor="FFEB9C")
    ai_status_fill_review = PatternFill("solid", fgColor="FFC7CE")
    
    # Find status column index in original headers
    status_col_idx = None
    for ci, h in enumerate(headers, 1):
        if h and h.lower() == "status":
            status_col_idx = ci
            break
    
    for row_idx, row_data in enumerate(rows_data, 2):
        # Normalize row dict to use lowercase keys
        norm = _normalize_row_dict(row_data)
        
        # Write original columns
        for ci, header in enumerate(headers, 1):
            h_lower = header.lower()
            val = norm.get(h_lower, "")
            ws.cell(row_idx, ci).value = str_val(val)
            
            # Color status column
            if ci == status_col_idx:
                sv = str(val).lower()
                if "ai_enhanced" in sv or "confirmed" in sv:
                    ws.cell(row_idx, ci).fill = ai_status_fill_confirmed
                elif "alias" in sv:
                    ws.cell(row_idx, ci).fill = ai_status_fill_alias
                elif "review" in sv:
                    ws.cell(row_idx, ci).fill = ai_status_fill_review
        
        # Write extra AI columns (already lowercase in the merged data)
        extra_keys = [
            "ai_extraction_method", "ai_confidence",
            "ai_normalization_notes", "ai_raw_row", "ai_table_context"
        ]
        for ei, ek in enumerate(extra_keys):
            c = n_orig + 1 + ei
            val = norm.get(ek, "")
            ws.cell(row_idx, c).value = str_val(val)
            ws.cell(row_idx, c).fill = PatternFill("solid", fgColor="DDEEFF")
    
    # Auto-width
    for c in range(1, n_orig + 1):
        ws.column_dimensions[get_column_letter(c)].width = 15
    for c in range(n_orig + 1, len(all_headers) + 1):
        ws.column_dimensions[get_column_letter(c)].width = 20


def _matrix_normalize(s: str) -> str:
    """Normalize a matrix symbol for matching AI parameters."""
    if not s:
        return ""
    import re
    # Remove spaces, underscores (merge), parens, dashes
    result = re.sub(r"[\s_\-()]", "", s).lower()
    # Handle specific cases like "rdson", "rthjc", "rthjh"
    result = result.replace("_", "")
    return result


def _extract_temperature(cond: str) -> str:
    """Extract temperature from condition string."""
    if not cond:
        return "unspecified"
    if "150°C" in cond or "T=150" in cond or "T=150°C" in cond:
        return "150°C"
    if "125°C" in cond or "T=125" in cond:
        return "125°C"
    if "25°C" in cond or "T=25" in cond or "TC=25" in cond:
        return "25°C"
    if "T=25°C" in cond:
        return "25°C"
    return "unspecified"


def _condition_key(sym: str, cond: str) -> str:
    """
    Build a condition-aware key for matching.
    For Clearance/Creepage: includes terminal type (T-T vs T-B).
    For others: includes temperature.

    Handles three cases:
    1. Explicit condition string (Terminal to Terminal / Terminal to Baseplate)
    2. Symbol contains T-B/T-T indicator (e.g., "Clearance (T-B)")
    3. Symbol normalized key contains _tb or _tt suffix
    """
    sym_lower = sym.lower()
    temp = _extract_temperature(cond)

    # For Clearance/Creepage: determine T-T vs T-B
    if "clearance" in sym_lower or "creepage" in sym_lower:
        cond_lower = cond.lower() if cond else ""

        # Check explicit condition string first
        if "terminal to terminal" in cond_lower or "t-t" in cond_lower:
            suffix = "_tt"
        elif "terminal to baseplate" in cond_lower or "t-b" in cond_lower or "baseplate" in cond_lower:
            suffix = "_tb"
        # Check if symbol itself indicates T-B or T-T
        # e.g., "Clearance (T-B)" or "Clearance (T-T)"
        elif "(t-b)" in sym_lower or " t-b" in sym_lower or "baseplate" in sym_lower:
            suffix = "_tb"
        elif "(t-t)" in sym_lower or " t-t" in sym_lower or "terminal to terminal" in sym_lower:
            suffix = "_tt"
        # Infer from normalized key if present in symbol
        # e.g., symbol="clearance_tb" or "creepage_tt"
        elif "_tb" in sym_lower:
            suffix = "_tb"
        elif "_tt" in sym_lower:
            suffix = "_tt"
        else:
            suffix = "_tt"  # default to T-T

        # Extract normalized symbol (without T-T/T-B suffix)
        # e.g., "Clearance (T-T)" -> "clearance"
        import re
        norm_sym = re.sub(r'\s*\([^)]*\)\s*$', '', sym_lower).strip()

        return f"{norm_sym}{suffix}"

    # RDS, VF, VGS: distinguish by temperature
    if any(k in sym_lower for k in ["rds", "vf", "vgs", "vgsth"]):
        return f"{sym_lower}_{temp}"

    return f"{sym_lower}_none"


def overlay_ai_on_matrix(
    ws,
    matrix_supplements: list[dict],
    part_number: str = "CAB530M12BM3",
):
    """
    Overlay AI confirmed values into the Comparison Matrix sheet.
    Only fills empty cells. Uses condition-aware exact matching.

    Fixes:
    1. Writes BOTH value AND unit from AI supplement
    2. Uses condition-aware matching for Clearance/Creepage
    3. Requires valid source_text before filling
    4. No fuzzy matching for Matrix overlay
    5. Marks conflicts with red highlight + conflict note (Task 1: Matrix conflict display)
    """
    headers = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]

    # Find CAB530M12BM3 columns
    val_col = cond_col = page_col = unit_col = notes_col = None
    for c in range(1, ws.max_column + 1):
        h = headers[c - 1] or ""
        if "CAB530M12BM3" in h:
            if "Value" in h and val_col is None:
                val_col = c
            elif "Condition" in h and cond_col is None:
                cond_col = c
            elif "Source Page" in h and page_col is None:
                page_col = c
        # Also find Unit column (col 4 is the shared Unit column)
        if h == "Unit":
            unit_col = c
        # Find Notes column
        if h == "Notes":
            notes_col = c

    if val_col is None:
        print(f"  [WARN] CAB530M12BM3 Value column not found in matrix")
        return 0

    print(f"  Matrix: val_col={val_col}, cond_col={cond_col}, page_col={page_col}, unit_col={unit_col}, notes_col={notes_col}")

    # Build matrix lookup with condition-aware keys
    # Matrix structure: col 2=Normalized, col 3=Symbol, col 4=Unit
    norm_key_to_row = {}      # normalized key (col 2) -> row
    sym_to_row = {}           # exact symbol (col 3) -> row
    cond_key_to_row = {}      # condition-aware key -> row
    all_rows = {}             # row_index -> {norm, sym, unit, cond}

    for r in range(2, ws.max_row + 1):
        norm_key = ws.cell(r, 2).value  # Normalized column
        sym = ws.cell(r, 3).value        # Symbol column
        unit = ws.cell(r, 4).value       # Unit column
        if norm_key:
            nk = _matrix_normalize(str(norm_key))
            norm_key_to_row[nk] = r
        if sym:
            sym_to_row[str(sym)] = r
        all_rows[r] = {"norm": norm_key, "sym": sym, "unit": unit}

    # Overlay AI supplements
    filled = 0
    skipped_no_src = 0
    conflicts = 0  # TASK 1: Track conflicts for conflict display
    for sup in matrix_supplements:
        sym = sup.get("symbol", "")
        ai_unit = sup.get("unit", "")
        ai_cond = sup.get("condition", "") or ""
        ai_source = sup.get("source_text", "") or ""
        ai_val = sup.get("value", "") or ""
        
        # TASK 3 FIX: Require valid source_text before filling
        if not ai_source or ai_source.strip() in ("", "-", "—", "N/A"):
            print(f"  [SKIP] {sym}: no valid source_text, cannot overlay")
            skipped_no_src += 1
            continue
        
        # TASK 1 FIX: Require non-empty value
        if _is_empty(ai_val):
            print(f"  [SKIP] {sym}: empty AI value")
            continue

        ai_norm = _matrix_normalize(sym)
        ai_cond_key = _condition_key(sym, ai_cond)

        row_idx = None
        match_type = ""

        # TASK 2 FIX: Condition-aware exact matching for Matrix overlay
        # Build condition_key_to_row from matrix
        if not cond_key_to_row:
            for r in range(2, ws.max_row + 1):
                msym = ws.cell(r, 3).value or ""
                mcond = ws.cell(r, 7).value or ""  # Condition column for this module
                mkey = _condition_key(msym, mcond)
                cond_key_to_row[mkey] = r

        # Strategy 1: Exact condition-aware key match (HIGHEST PRIORITY)
        if ai_cond_key in cond_key_to_row:
            row_idx = cond_key_to_row[ai_cond_key]
            match_type = "condition_exact"
        
        # Strategy 2: Direct normalized key match (only if no condition match)
        if row_idx is None and ai_norm in norm_key_to_row:
            row_idx = norm_key_to_row[ai_norm]
            match_type = "norm_exact"

        # Strategy 3: Symbol exact match (only if no condition match)
        if row_idx is None and sym in sym_to_row:
            row_idx = sym_to_row[sym]
            match_type = "symbol_exact"

        # NO fuzzy matching for Matrix overlay (Task 2 fix)

        if row_idx is None:
            print(f"  [SKIP] {sym}: no matching matrix row")
            continue

        current_val = ws.cell(row_idx, val_col).value
        if not _is_empty(current_val):
            # Already filled - check for conflict
            existing = str(current_val).strip()
            if existing and ai_val and existing != ai_val:
                # TASK 1 FIX: Mark conflict with red highlight + conflict note
                red = PatternFill("solid", fgColor="FF6B6B")  # Red for conflict
                ws.cell(row_idx, val_col).fill = red

                # Write conflict note in Condition column (col 7) or Notes column (col 15)
                ai_unit_str = f" {ai_unit}" if ai_unit else ""
                existing_unit = str(ws.cell(row_idx, unit_col).value or "").strip()
                existing_unit_str = f" {existing_unit}" if existing_unit else ""
                conflict_note = f"conflict: v1.0={existing}{existing_unit_str}; ai={ai_val}{ai_unit_str}; see Needs Review"

                if cond_col:
                    ws.cell(row_idx, cond_col).value = conflict_note
                    ws.cell(row_idx, cond_col).fill = red
                elif notes_col:
                    ws.cell(row_idx, notes_col).value = conflict_note
                    ws.cell(row_idx, notes_col).fill = red

                conflicts += 1
                print(f"  [CONFLICT] {sym}: matrix has '{existing}', AI has '{ai_val}'")
            continue

        # TASK 1 FIX: Write BOTH value AND unit
        ws.cell(row_idx, val_col).value = str_val(ai_val)
        if unit_col and ai_unit:
            ws.cell(row_idx, unit_col).value = ai_unit
        if cond_col:
            ws.cell(row_idx, cond_col).value = str_val(ai_cond)
        if page_col:
            ws.cell(row_idx, page_col).value = str_val(sup.get("source_page", ""))

        # Yellow highlight = AI enhanced
        yellow = PatternFill("solid", fgColor="FFFF99")
        ws.cell(row_idx, val_col).fill = yellow
        if unit_col and ai_unit:
            ws.cell(row_idx, unit_col).fill = yellow
        if cond_col:
            ws.cell(row_idx, cond_col).fill = yellow
        if page_col:
            ws.cell(row_idx, page_col).fill = yellow

        filled += 1
        print(f"  Matrix fill [{filled}] ({match_type}): {sym} = {ai_val} {ai_unit} [row {row_idx}]")

    if skipped_no_src > 0:
        print(f"  [INFO] Skipped {skipped_no_src} entries due to missing source_text")
    if conflicts > 0:
        print(f"  [INFO] Marked {conflicts} conflicts with red highlight")

    return filled, conflicts


def _infer_condition_class(field: str, ai_value: str) -> str:
    """
    Infer condition class for Clearance/Creepage when condition_class is None.
    Uses value-based thresholds from make_condition_aware_key.
    """
    field_lower = field.lower()
    if "clearance" in field_lower:
        try:
            val = float(ai_value)
            return "clearance_tb" if val >= 15 else "clearance_tt"
        except (ValueError, TypeError):
            return "clearance_tt"
    elif "creepage" in field_lower:
        try:
            val = float(ai_value)
            return "creepage_tb" if val >= 35 else "creepage_tt"
        except (ValueError, TypeError):
            return "creepage_tt"
    return ""


def mark_matrix_conflicts_from_needs_review(
    ws,
    needs_review: list[dict],
    part_number: str = "CAB530M12BM3",
):
    """
    Mark Matrix conflicts for entries in needs_review.
    This handles cases like Clearance/Creepage where v1.0 already has a value
    but AI found a different value - these go to needs_review instead of matrix_supplements.

    For each needs_review entry with condition_class and non-empty v1_value:
    - Find the corresponding Matrix row using condition_class
    - Compare v1.0 value with AI value
    - If different, mark with red highlight and conflict note
    """
    headers = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]

    # Find CAB530M12BM3 columns
    val_col = cond_col = unit_col = None
    for c in range(1, ws.max_column + 1):
        h = headers[c - 1] or ""
        if "CAB530M12BM3" in h:
            if "Value" in h and val_col is None:
                val_col = c
            elif "Condition" in h and cond_col is None:
                cond_col = c
        if h == "Unit":
            unit_col = c

    if val_col is None:
        print(f"  [WARN] CAB530M12BM3 Value column not found in matrix")
        return 0

    # Build condition_class to Matrix row lookup from Normalized column (col 2)
    cond_class_to_row = {}
    for r in range(2, ws.max_row + 1):
        norm_key = ws.cell(r, 2).value
        if norm_key:
            cond_class_to_row[str(norm_key).strip()] = r

    marked = 0

    # Red fill for conflicts
    red = PatternFill("solid", fgColor="FF6B6B")

    for entry in needs_review:
        condition_class = entry.get("condition_class", "") or ""
        v1_value = entry.get("v1_value", "")
        ai_value = entry.get("ai_value", "")
        field = entry.get("field", "")
        unit = entry.get("unit", "")

        # Skip if no v1_value
        if not v1_value:
            continue

        # Skip if v1_value is empty string
        if str(v1_value).strip() == "":
            continue

        # If condition_class is None, try to infer it for Clearance/Creepage
        if not condition_class:
            condition_class = _infer_condition_class(field, ai_value)

        # Skip if still no condition_class
        if not condition_class:
            continue

        # Find Matrix row for this condition_class
        if condition_class not in cond_class_to_row:
            # Try to find by symbol - some entries might have partial matching
            # For Clearance/Creepage, the condition_class should match the Normalized key
            continue

        row_idx = cond_class_to_row[condition_class]

        # Get current Matrix value
        current_val = ws.cell(row_idx, val_col).value
        if current_val is None:
            current_val = ""
        current_val_str = str(current_val).strip()

        # Skip if Matrix value is empty (not a conflict case)
        if current_val_str == "":
            continue

        # Skip if values are the same
        if current_val_str == str(ai_value).strip():
            continue

        # Mark conflict with red highlight
        ws.cell(row_idx, val_col).fill = red

        # Get existing unit from Matrix
        matrix_unit = ws.cell(row_idx, unit_col).value or ""
        if not matrix_unit and unit:
            matrix_unit = unit

        # Write conflict note in Condition column
        v1_unit_str = f" {matrix_unit}" if matrix_unit else ""
        ai_unit_str = f" {unit}" if unit else ""
        conflict_note = f"conflict: v1.0={current_val_str}{v1_unit_str}; ai={ai_value}{ai_unit_str}; see Needs Review"

        if cond_col:
            ws.cell(row_idx, cond_col).value = conflict_note
            ws.cell(row_idx, cond_col).fill = red

        marked += 1
        print(f"  [CONFLICT from needs_review] {field} ({condition_class}): matrix='{current_val_str}', AI='{ai_value}'")

    if marked > 0:
        print(f"  [INFO] Marked {marked} additional conflicts from needs_review")

    return marked


def write_ai_parameters_sheet(wb, ai_params: list[dict], part_number: str):
    """Add AI Parameters sheet."""
    if "AI Parameters" in wb.sheetnames:
        del wb["AI Parameters"]

    ws = wb.create_sheet("AI Parameters", 6)  # position 6

    headers = [
        "Part Number", "Category", "Section", "Symbol", "Parameter",
        "Min", "Typ", "Max", "Value", "Unit", "Condition",
        "Source Page", "Status", "Confidence", "Extraction Method",
        "Source Text", "Raw Row", "Table Context", "Normalization Notes"
    ]

    # Header
    hf = PatternFill("solid", fgColor="4472C4")
    hfont = Font(bold=True, color="FFFFFF")
    for c, h in enumerate(headers, 1):
        cell = ws.cell(1, c)
        cell.value = h
        cell.font = hfont
        cell.fill = hf
        cell.alignment = Alignment(horizontal="center", wrap_text=True)

    # Data
    cf = PatternFill("solid", fgColor="C6EFCE")
    af = PatternFill("solid", fgColor="FFEB9C")
    rf = PatternFill("solid", fgColor="FFC7CE")

    data = build_ai_parameters_sheet_data(ai_params, part_number)
    for ri, row_data in enumerate(data, 2):
        for ci, key in enumerate(headers, 1):
            val = str_val(row_data.get(key, ""))
            cell = ws.cell(ri, ci)
            cell.value = val
            cell.alignment = Alignment(wrap_text=True)

            if key == "Status":
                vl = val.lower()
                if "confirmed" in vl:
                    cell.fill = cf
                elif "alias" in vl:
                    cell.fill = af
                elif "review" in vl:
                    cell.fill = rf

    # Column widths
    widths = [20, 15, 25, 20, 30, 8, 8, 8, 12, 8, 35, 12, 20, 10, 18, 40, 40, 30, 30]
    for c, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(c)].width = w

    print(f"  AI Parameters: {len(data)} rows")


def write_ai_evaluation_sheet(wb, part_number: str):
    """Add AI Evaluation sheet."""
    if "AI Evaluation" in wb.sheetnames:
        del wb["AI Evaluation"]

    ws = wb.create_sheet("AI Evaluation", 7)  # position 7

    data = build_ai_evaluation_sheet_data(part_number)
    headers = list(data[0].keys())

    hf = PatternFill("solid", fgColor="70AD47")
    hfont = Font(bold=True, color="FFFFFF")
    for c, h in enumerate(headers, 1):
        cell = ws.cell(1, c)
        cell.value = h
        cell.font = hfont
        cell.fill = hf
        cell.alignment = Alignment(horizontal="center", wrap_text=True)

    for ri, row_data in enumerate(data, 2):
        for ci, key in enumerate(headers, 1):
            val = str_val(row_data.get(key, ""))
            cell = ws.cell(ri, ci)
            cell.value = val
            cell.alignment = Alignment(wrap_text=True)

            if key == "result":
                if val == "PASS":
                    cell.fill = PatternFill("solid", fgColor="C6EFCE")
                else:
                    cell.fill = PatternFill("solid", fgColor="FFC7CE")

    for c in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(c)].width = 18

    print(f"  AI Evaluation: {len(data)} rows")


def main():
    parser = argparse.ArgumentParser(description="Build AI-enhanced Excel")
    parser.add_argument("--base-excel", required=True)
    parser.add_argument("--ai-json", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    # Load AI JSON
    print(f"Loading AI JSON: {args.ai_json}")
    with open(args.ai_json) as f:
        raw = json.load(f)
    ai_params = raw.get("normalized_parameters", raw.get("parameters", []))
    confirmed = sum(1 for p in ai_params if p.get("status") == "confirmed")
    alias_review = sum(1 for p in ai_params if p.get("status") == "needs_alias_review")
    needs_review = sum(1 for p in ai_params if p.get("status") == "needs_review")
    print(f"  Total: {len(ai_params)}, confirmed={confirmed}, alias_review={alias_review}, needs_review={needs_review}")

    # Copy base
    print(f"Copying base: {args.base_excel}")
    shutil.copy2(args.base_excel, args.output)

    wb = openpyxl.load_workbook(args.output)

    # === Load All Parameters ===
    ws_ap = wb["All Parameters"]
    ap_headers, ap_rows = load_all_params_as_tuples(ws_ap)
    print(f"  All Parameters: {len(ap_rows)} rows, {len(ap_headers)} cols")

    # Convert to dicts for merge
    ap_dicts = []
    for row in ap_rows:
        d = {}
        for ci, h in enumerate(ap_headers):
            d[h] = row[ci]
        ap_dicts.append(d)

    # === Merge ===
    print("Merging AI parameters...")
    merged_dicts, merge_nr, matrix_supps = merge_parameters(
        ap_dicts, ai_params, part_number="CAB530M12BM3"
    )
    print(f"  Merged rows: {len(merged_dicts)}, Needs Review: {len(merge_nr)}, Matrix supplements: {len(matrix_supps)}")

    # Convert merged dicts back to rows (using original header order)
    # Extra columns for AI metadata
    extra_cols = [
        "AI Extraction Method", "AI Confidence",
        "AI Normalization Notes", "AI Raw Row", "AI Table Context"
    ]

    merged_rows = []
    for d in merged_dicts:
        orig_vals = [str_val(d.get(h, "")) for h in ap_headers]
        extra_vals = [
            str_val(d.get("ai_extraction_method", "")),
            str_val(d.get("ai_confidence", "")),
            str_val(d.get("ai_normalization_notes", "")),
            str_val(d.get("ai_raw_row", "")),
            str_val(d.get("ai_table_context", "")),
        ]
        merged_rows.append(orig_vals + extra_vals)

    # === Write enhanced All Parameters ===
    # Clear and rewrite
    ws_ap.delete_rows(1, ws_ap.max_row)
    # merged_dicts is list[dict] - pass directly
    write_all_params_enhanced(ws_ap, ap_headers, merged_dicts, extra_cols)
    print(f"  All Parameters written: {len(merged_rows)} rows + {len(extra_cols)} AI cols")

    # === Overlay on Comparison Matrix ===
    print("Overlaying AI on Comparison Matrix...")
    ws_mat = wb["Comparison Matrix"]
    filled, conflicts = overlay_ai_on_matrix(ws_mat, matrix_supps, "CAB530M12BM3")
    print(f"  Matrix cells filled: {filled}, conflicts: {conflicts}")

    # === Mark additional conflicts from needs_review (e.g., Clearance/Creepage) ===
    additional_conflicts = mark_matrix_conflicts_from_needs_review(ws_mat, merge_nr, "CAB530M12BM3")
    conflicts += additional_conflicts

    # === Add AI Needs Review to Needs Review sheet ===
    if merge_nr and "Needs Review" in wb.sheetnames:
        ws_nr = wb["Needs Review"]
        start_r = ws_nr.max_row + 1
        yellow = PatternFill("solid", fgColor="FFEB9C")
        for i, entry in enumerate(merge_nr):
            r = start_r + i
            ws_nr.cell(r, 1).value = str_val(entry.get("part_number", ""))
            ws_nr.cell(r, 2).value = str_val(entry.get("field", ""))
            ws_nr.cell(r, 3).value = str_val(entry.get("category", ""))
            ws_nr.cell(r, 4).value = str_val(entry.get("v1_value", ""))
            ws_nr.cell(r, 5).value = str_val(entry.get("ai_value", ""))
            ws_nr.cell(r, 6).value = str_val(entry.get("unit", ""))
            ws_nr.cell(r, 7).value = str_val(entry.get("source_page", ""))
            ws_nr.cell(r, 8).value = str_val(entry.get("issue", ""))
            for c in range(1, 9):
                ws_nr.cell(r, c).fill = yellow
        print(f"  Needs Review: added {len(merge_nr)} AI entries")

    # === Add AI sheets ===
    print("Adding AI sheets...")
    write_ai_parameters_sheet(wb, ai_params, "CAB530M12BM3")
    write_ai_evaluation_sheet(wb, "CAB530M12BM3")

    # === Reorder sheets ===
    desired = [
        "Comparison Matrix", "Quick View", "All Parameters", "Needs Review",
        "Raw Tables", "Summary", "AI Parameters", "AI Evaluation",
    ]
    for i, name in enumerate(desired):
        if name in wb.sheetnames:
            wb.move_sheet(name, offset=i - wb.sheetnames.index(name))

    wb.save(args.output)
    wb.close()

    print(f"\n✅ Saved: {args.output}")
    print(f"\n=== Final Report ===")
    print(f"  Output: {args.output}")
    print(f"  Sheets: {desired}")
    print(f"  AI params: {len(ai_params)} total")
    print(f"    confirmed: {confirmed}")
    print(f"    needs_alias_review: {alias_review}")
    print(f"    needs_review: {needs_review}")
    print(f"  Matrix filled: {filled} cells")
    print(f"  Matrix conflicts: {conflicts} cells (marked red)")
    print(f"  Needs Review added: {len(merge_nr)} entries")


if __name__ == "__main__":
    main()
