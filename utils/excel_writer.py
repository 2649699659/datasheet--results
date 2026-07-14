"""
Excel Output Writer v1

Generates final_comparison.xlsx from Final Selector v1 document-based output.

Sheets:
    1. Final Comparison - final_candidate fields with Value/Condition/Page per document
    2. Review Needed - review_needed fields with all candidates + Condition
    3. Blocked - blocked fields with danger reasons + Condition
    4. Source Evidence - source text for all non-missing selections + Condition

Step 7.4: Added Condition column to all sheets, Value/Condition/Page per-document layout.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter


# =============================================================================
# Helper Functions
# =============================================================================

def _normalize_degrees(text: str) -> str:
    """Normalize degree symbol variants to standard °C."""
    if not text:
        return text
    # Replace various degree-like characters with standard °
    for variant in ("\u00b0", "\u2070", "\u00b2", "\u33f2", "\uf0b0", "\u2103", "\u33f1"):
        text = text.replace(variant, "\u00b0")
    # Normalize µ to μ
    text = text.replace("\u00b5", "\u03bc")  # micro sign → greek mu
    text = text.replace("\u03bc", "\u03bc")  # already greek mu
    return text


# Condition extraction: (compiled_regex, key_name_or_static)
# Static strings: use as-is (condition keyword)
# Key names (str, non-static): capture VALUE via group(1), output key=value
# Static keyword list for disambiguation:
_STATIC_KEYWORDS = frozenset(["Terminal to Terminal", "Terminal to Baseplate", "VDS=VGS"])

_DEGREE_CHARS = r"\u00b0|\u2070|\u2103|\u33f1|\uf0b0"  # standard °, ⁰, ℃, ³⁄₂, CJK ˚

_CONDITION_PATTERNS = [
    # Static keywords
    (re.compile(r"Terminal\s+to\s+Terminal", re.IGNORECASE), "Terminal to Terminal"),
    (re.compile(r"Terminal\s+to\s+Baseplate", re.IGNORECASE), "Terminal to Baseplate"),
    # VDS=VGS style (letter=letter, no numeric value) — VGS(th) specific
    (re.compile(r"V\s*=\s*V\s*;", re.IGNORECASE), "VDS=VGS"),
    # Temperature with degree variants (no space required before degree/C)
    (re.compile(rf"TC\s*=\s*([-\d.]+)\s*(?:{_DEGREE_CHARS}|[Cc]|degrees?\s+C)", re.IGNORECASE), "TC"),
    (re.compile(rf"TJ\s*=\s*([-\d.]+)\s*(?:{_DEGREE_CHARS}|[Cc]|degrees?\s+C)", re.IGNORECASE), "TJ"),
    (re.compile(rf"Tj\s*=\s*([-\d.]+)\s*(?:{_DEGREE_CHARS}|[Cc]|degrees?\s+C)", re.IGNORECASE), "TJ"),
    (re.compile(rf"T\s*=\s*([-\d.]+)\s*(?:{_DEGREE_CHARS}|[Cc]|degrees?\s+C)", re.IGNORECASE), "T"),
    # Load (inductor energy test)
    (re.compile(r"Load\s*=\s*([\d.]+)\s*(?:\u03bc|mu)?\s*H", re.IGNORECASE), "Load"),
    # RG / R (gate resistance / load resistance)
    (re.compile(r"RG\(ext\)\s*=\s*([\d.]+)\s*(?:\u03a9|ohm)", re.IGNORECASE), "RG(ext)"),
    (re.compile(r"RG\s*=\s*([\d.]+)\s*(?:\u03a9|ohm)", re.IGNORECASE), "RG"),
    (re.compile(r"R\s*=\s*([\d.]+)\s*(?:\u03a9|ohm)", re.IGNORECASE), "R"),
    # Frequency
    (re.compile(r"f\s*=\s*([\d.]+)\s*Hz", re.IGNORECASE), "f"),
    # Voltage (specific keys first, then general)
    (re.compile(r"VGS\s*=\s*([-\d./]+)\s*V", re.IGNORECASE), "VGS"),
    (re.compile(r"VDS\s*=\s*([-\d./]+)\s*V", re.IGNORECASE), "VDS"),
    (re.compile(r"VDD\s*=\s*([-\d./]+)\s*V", re.IGNORECASE), "VDD"),
    (re.compile(r"VR\s*=\s*([-\d./]+)\s*V", re.IGNORECASE), "VR"),
    (re.compile(r"\bV\s*=\s*([-\d./]+)\s*V\b", re.IGNORECASE), "V"),
    # Current (specific keys first)
    (re.compile(r"ID\s*=\s*([-\d.]+)\s*mA", re.IGNORECASE), "ID"),
    (re.compile(r"IF\s*=\s*([-\d.]+)\s*mA", re.IGNORECASE), "IF"),
    (re.compile(r"IRM\s*=\s*([-\d.]+)\s*mA", re.IGNORECASE), "IRM"),
    (re.compile(r"IR\s*=\s*([-\d.]+)\s*mA", re.IGNORECASE), "IR"),
    (re.compile(r"I\s*=\s*([-\d.]+)\s*mA", re.IGNORECASE), "I"),
    # Without mA prefix (pure A)
    (re.compile(r"ID\s*=\s*([-\d.]+)\s*A", re.IGNORECASE), "ID"),
    (re.compile(r"IF\s*=\s*([-\d.]+)\s*A", re.IGNORECASE), "IF"),
    (re.compile(r"IRM?\s*=\s*([-\d.]+)\s*A", re.IGNORECASE), "IRM"),
    (re.compile(r"I\s*=\s*([-\d.]+)\s*A", re.IGNORECASE), "I"),
]


def format_condition(param: Optional[Dict[str, Any]]) -> str:
    """
    Format condition string from param dict.

    Priority:
        1. param["condition"]  (already normalized string)
        2. param["condition_values"]  (list joined with "; ")
        3. Extract from param["source_text"]  (specific patterns)

    Returns normalized condition string, never modifies param values.
    """
    if not param:
        return ""

    # Priority 1: condition field
    cond = param.get("condition") or ""
    if cond.strip():
        return _normalize_degrees(cond.strip())

    # Priority 2: condition_values list
    cv = param.get("condition_values") or []
    if cv and any(str(v).strip() for v in cv):
        parts = []
        for v in cv:
            s = str(v).strip()
            if s:
                parts.append(s)
        if parts:
            return _normalize_degrees("; ".join(parts))

    # Priority 3: extract from source_text
    src = param.get("source_text") or ""
    return _extract_condition_from_text(src)


def _extract_condition_from_text(src: str) -> str:
    """Extract condition snippets from raw source_text."""
    if not src or len(src) > 2000:
        return ""

    # Normalize: remove spaces around = for cleaner key=value matching
    # "V =18V" -> "V=18V", "I =150A" -> "I=150A"
    # But preserve degree chars: "T =25°C" -> "T=25°C" (normalizes to standard °)
    normalized = src
    for deg in ("\u00b0", "\u2070", "\u2103", "\u33f1", "\uf0b0", "\u33f2"):
        normalized = normalized.replace(deg, "\u00b0")
    normalized = re.sub(r"(\w)\s*=\s*", r"\1=", normalized)

    parts: List[str] = []
    seen: set = set()

    for pattern, key_or_static in _CONDITION_PATTERNS:
        m = pattern.search(normalized)
        if not m:
            continue
        # Static keyword: add as-is, no capture group
        if isinstance(key_or_static, str) and key_or_static in _STATIC_KEYWORDS:
            if key_or_static not in seen:
                parts.append(key_or_static)
                seen.add(key_or_static)
            continue
        # Dynamic key+value: requires capture group
        if isinstance(key_or_static, str) and key_or_static not in _STATIC_KEYWORDS:
            if m.lastindex and m.lastindex >= 1:
                val = m.group(1)
                snippet = f"{key_or_static}={val}"
                if snippet not in seen and len(snippet) < 30:
                    parts.append(snippet)
                    seen.add(snippet)

    # Limit to most relevant (first 6)
    result = "; ".join(parts[:6])
    return _normalize_degrees(result)


def get_param_unit(param: Optional[Dict[str, Any]]) -> str:
    """Get unit from param dict, in priority order."""
    if not param:
        return ""
    return param.get("original_unit") or param.get("normalized_unit") or param.get("unit") or ""


def format_param_value(param: Optional[Dict[str, Any]]) -> str:
    """Format parameter value as string per spec rules."""
    if not param:
        return ""

    val = param.get("value")
    min_val = param.get("min")
    typ = param.get("typ")
    max_val = param.get("max")

    parts = []
    if min_val is not None:
        parts.append(f"min={min_val}")
    if typ is not None:
        parts.append(f"typ={typ}")
    if max_val is not None:
        parts.append(f"max={max_val}")

    if not parts:
        if val is not None:
            return str(val)
        return ""

    # Format based on which values exist
    if min_val is not None and max_val is not None and typ is None:
        return f"{min_val} ~ {max_val}"
    if typ is not None and max_val is not None and min_val is None:
        return f"typ={typ}; max={max_val}"
    if len(parts) >= 2:
        return "; ".join(parts)
    return parts[0] if parts else (str(val) if val is not None else "")


def get_document_display_name(doc: Dict[str, Any]) -> str:
    """Get display name for a document."""
    pdf_stem = doc.get("pdf_stem") or ""
    file_name = doc.get("file_name") or ""
    if pdf_stem:
        return pdf_stem
    if file_name:
        return file_name
    return "unknown"


def _shorten_source_text(text: str, max_len: int = 300) -> str:
    """Shorten source text to max_len, preserve start."""
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


# =============================================================================
# Column Definitions (v1: Value / Condition / Page per document)
# =============================================================================

# Final Comparison: Parameter | Unit | [DocName Value] | [DocName Condition] | [DocName Page] | Notes
# Review Needed: Document | Field ID | Label | Candidate Type | Value | Unit | Condition | Score | Reason | Warnings | Page | Table | Row | Source Text
# Blocked: Document | Field ID | Label | Block Reason | Value | Unit | Condition | Page | Source Text
# Source Evidence: Document | Field ID | Selection Status | Value | Unit | Condition | Page | Table | Row | Source Hash | Source Text


# =============================================================================
# Sheet Writers
# =============================================================================

def _write_header_row(ws, cols: List[str], row: int = 1) -> None:
    """Write a bold header row."""
    for col_idx, col_name in enumerate(cols, start=1):
        cell = ws.cell(row=row, column=col_idx, value=col_name)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def _set_col_width(ws, col_idx: int, width: float) -> None:
    col_letter = get_column_letter(col_idx)
    ws.column_dimensions[col_letter].width = width


def _write_final_comparison(ws, selection_result: Dict[str, Any]) -> None:
    """
    Write Final Comparison sheet (Sheet 1).

    Per-document columns: Value | Condition | Page
    Column layout: Parameter | Unit | [Doc1 Value] | [Doc1 Condition] | [Doc1 Page] | ... | Notes
    """
    docs = selection_result.get("documents", [])

    # Build column headers
    # Per document: Value | Condition | Page (3 cols each)
    doc_cols: List[Tuple[str, int]] = []  # (doc_name, start_col)
    header = ["Parameter", "Unit"]
    for doc in docs:
        doc_name = get_document_display_name(doc)
        start_col = len(header) + 1
        doc_cols.append((doc_name, start_col))
        header.extend([f"{doc_name} Value", f"{doc_name} Condition", f"{doc_name} Page"])

    _write_header_row(ws, header, row=1)
    ws.freeze_panes = "C2"

    # Build doc_field_map
    doc_field_map = []
    for doc in docs:
        field_map = {}
        for f in doc.get("fields", []):
            field_map[f["field_id"]] = f
        doc_field_map.append(field_map)

    # Ordered fields (final_candidate only)
    all_final_ids = set()
    for dmap in doc_field_map:
        for fid, f in dmap.items():
            if f.get("selection_status") == "final_candidate":
                all_final_ids.add(fid)

    if docs and docs[0].get("fields"):
        ordered_fields = [f["field_id"] for f in docs[0]["fields"] if f["field_id"] in all_final_ids]
    else:
        ordered_fields = sorted(all_final_ids)

    row = 2
    for fid in ordered_fields:
        # Get label
        label = fid
        for dmap in doc_field_map:
            if fid in dmap:
                label = dmap[fid].get("label") or fid
                break
        ws.cell(row=row, column=1, value=label)
        ws.cell(row=row, column=1).font = Font(bold=True)

        # Get unit from first doc
        unit = ""
        for dmap in doc_field_map:
            if fid in dmap:
                p = dmap[fid].get("selected_param")
                if p:
                    unit = get_param_unit(p)
                    break
        ws.cell(row=row, column=2, value=unit)

        # Per-document columns
        for doc_idx, (doc_name, start_col) in enumerate(doc_cols):
            dmap = doc_field_map[doc_idx]
            if fid not in dmap:
                continue
            f = dmap[fid]
            if f.get("selection_status") != "final_candidate":
                continue
            p = f.get("selected_param")

            value_col = start_col
            cond_col = start_col + 1
            page_col = start_col + 2

            # Value
            value_str = format_param_value(p)
            ws.cell(row=row, column=value_col, value=value_str)

            # Condition
            cond_str = format_condition(p)
            ws.cell(row=row, column=cond_col, value=cond_str)
            ws.cell(row=row, column=cond_col).alignment = Alignment(wrap_text=True)

            # Page
            page_val = str(p.get("source_page", "")) if p else ""
            ws.cell(row=row, column=page_col, value=page_val)

        row += 1

    # Column widths
    _set_col_width(ws, 1, 22)  # Parameter
    _set_col_width(ws, 2, 8)   # Unit
    for doc_name, start_col in doc_cols:
        _set_col_width(ws, start_col, 22)     # Value
        _set_col_width(ws, start_col + 1, 30) # Condition
        _set_col_width(ws, start_col + 2, 8)  # Page


def _write_review_needed(ws, selection_result: Dict[str, Any]) -> None:
    """
    Write Review Needed sheet (Sheet 2).

    Columns: Document | Field ID | Label | Candidate Type | Value | Unit | Condition | Score | Reason | Warnings | Page | Table | Row | Source Text
    """
    cols = [
        "Document", "Field ID", "Label", "Candidate Type",
        "Value", "Unit", "Condition",
        "Score", "Reason", "Warnings",
        "Page", "Table", "Row", "Source Text",
    ]
    _write_header_row(ws, cols, row=1)
    ws.freeze_panes = "A2"

    row = 2
    for doc in selection_result.get("documents", []):
        doc_name = get_document_display_name(doc)
        for f in doc.get("fields", []):
            if f.get("selection_status") != "review_needed":
                continue

            fid = f["field_id"]
            label = f.get("label") or fid
            score = f.get("selector_score", 0)
            reason = f.get("selector_reason", "")
            warnings = "; ".join(f.get("selector_warnings", [])[:3])

            # Primary selected candidate
            p = f.get("selected_param")
            value_str = format_param_value(p)
            unit = get_param_unit(p)
            cond_str = format_condition(p)
            page = p.get("source_page", "") if p else ""
            table_idx = p.get("table_index", "") if p else ""
            row_idx = p.get("row_index", "") if p else ""
            source_text = _shorten_source_text(p.get("source_text", "") if p else "")

            ws.cell(row=row, column=1, value=doc_name)
            ws.cell(row=row, column=2, value=fid)
            ws.cell(row=row, column=3, value=label)
            ws.cell(row=row, column=4, value="selected")
            ws.cell(row=row, column=5, value=value_str)
            ws.cell(row=row, column=6, value=unit)
            ws.cell(row=row, column=7, value=cond_str)
            ws.cell(row=row, column=7).alignment = Alignment(wrap_text=True)
            ws.cell(row=row, column=8, value=score)
            ws.cell(row=row, column=9, value=reason[:300])
            ws.cell(row=row, column=10, value=warnings[:100])
            ws.cell(row=row, column=11, value=str(page) if page else "")
            ws.cell(row=row, column=12, value=str(table_idx) if table_idx != "" else "")
            ws.cell(row=row, column=13, value=str(row_idx) if row_idx != "" else "")
            ws.cell(row=row, column=14, value=source_text)
            ws.cell(row=row, column=14).alignment = Alignment(wrap_text=True)
            row += 1

            # Alternative candidates
            for alt in f.get("review_params", []):
                alt_value_str = format_param_value(alt)
                alt_unit = get_param_unit(alt)
                alt_cond_str = format_condition(alt)
                alt_page = alt.get("source_page", "")
                alt_table = alt.get("table_index", "")
                alt_row = alt.get("row_index", "")
                alt_text = _shorten_source_text(alt.get("source_text", ""))
                alt_reason = alt.get("review_reason", "")

                ws.cell(row=row, column=1, value=doc_name)
                ws.cell(row=row, column=2, value=fid)
                ws.cell(row=row, column=3, value=label)
                ws.cell(row=row, column=4, value="alternative_review")
                ws.cell(row=row, column=5, value=alt_value_str)
                ws.cell(row=row, column=6, value=alt_unit)
                ws.cell(row=row, column=7, value=alt_cond_str)
                ws.cell(row=row, column=7).alignment = Alignment(wrap_text=True)
                ws.cell(row=row, column=8, value="")
                ws.cell(row=row, column=9, value=alt_reason[:300])
                ws.cell(row=row, column=10, value="")
                ws.cell(row=row, column=11, value=str(alt_page) if alt_page else "")
                ws.cell(row=row, column=12, value=str(alt_table) if alt_table != "" else "")
                ws.cell(row=row, column=13, value=str(alt_row) if alt_row != "" else "")
                ws.cell(row=row, column=14, value=alt_text)
                ws.cell(row=row, column=14).alignment = Alignment(wrap_text=True)
                row += 1

    # Column widths
    _set_col_width(ws, 1, 20)   # Document
    _set_col_width(ws, 2, 18)   # Field ID
    _set_col_width(ws, 3, 20)   # Label
    _set_col_width(ws, 4, 18)   # Candidate Type
    _set_col_width(ws, 5, 20)   # Value
    _set_col_width(ws, 6, 8)    # Unit
    _set_col_width(ws, 7, 35)   # Condition
    _set_col_width(ws, 8, 8)    # Score
    _set_col_width(ws, 9, 40)   # Reason
    _set_col_width(ws, 10, 30)  # Warnings
    _set_col_width(ws, 11, 6)   # Page
    _set_col_width(ws, 12, 6)   # Table
    _set_col_width(ws, 13, 6)    # Row
    _set_col_width(ws, 14, 60)  # Source Text


def _write_blocked(ws, selection_result: Dict[str, Any]) -> None:
    """
    Write Blocked sheet (Sheet 3).

    Columns: Document | Field ID | Label | Block Reason | Value | Unit | Condition | Page | Source Text
    """
    cols = [
        "Document", "Field ID", "Label", "Block Reason",
        "Value", "Unit", "Condition", "Page", "Source Text",
    ]
    _write_header_row(ws, cols, row=1)
    ws.freeze_panes = "A2"

    row = 2
    for doc in selection_result.get("documents", []):
        doc_name = get_document_display_name(doc)
        for f in doc.get("fields", []):
            if f.get("selection_status") != "blocked":
                continue

            fid = f["field_id"]
            label = f.get("label") or fid
            reason = f.get("selector_reason", "")
            p = f.get("selected_param")
            value_str = format_param_value(p)
            unit = get_param_unit(p)
            cond_str = format_condition(p)
            page = p.get("source_page", "") if p else ""
            source_text = _shorten_source_text(p.get("source_text", "") if p else "")

            ws.cell(row=row, column=1, value=doc_name)
            ws.cell(row=row, column=2, value=fid)
            ws.cell(row=row, column=3, value=label)
            ws.cell(row=row, column=4, value=reason[:300])
            ws.cell(row=row, column=5, value=value_str)
            ws.cell(row=row, column=6, value=unit)
            ws.cell(row=row, column=7, value=cond_str)
            ws.cell(row=row, column=7).alignment = Alignment(wrap_text=True)
            ws.cell(row=row, column=8, value=str(page) if page else "")
            ws.cell(row=row, column=9, value=source_text)
            ws.cell(row=row, column=9).alignment = Alignment(wrap_text=True)
            row += 1

    # Column widths
    _set_col_width(ws, 1, 20)  # Document
    _set_col_width(ws, 2, 18)  # Field ID
    _set_col_width(ws, 3, 20)  # Label
    _set_col_width(ws, 4, 45)  # Block Reason
    _set_col_width(ws, 5, 20)  # Value
    _set_col_width(ws, 6, 8)   # Unit
    _set_col_width(ws, 7, 35)  # Condition
    _set_col_width(ws, 8, 6)   # Page
    _set_col_width(ws, 9, 60)  # Source Text


def _write_source_evidence(ws, selection_result: Dict[str, Any]) -> None:
    """
    Write Source Evidence sheet (Sheet 4).

    Columns: Document | Field ID | Selection Status | Value | Unit | Condition | Page | Table | Row | Source Hash | Source Text
    """
    cols = [
        "Document", "Field ID", "Selection Status",
        "Value", "Unit", "Condition",
        "Page", "Table", "Row", "Source Hash", "Source Text",
    ]
    _write_header_row(ws, cols, row=1)
    ws.freeze_panes = "A2"

    row = 2
    for doc in selection_result.get("documents", []):
        doc_name = get_document_display_name(doc)
        doc_id = doc.get("document_id", "")
        for f in doc.get("fields", []):
            status = f.get("selection_status", "")
            if status == "missing":
                continue

            fid = f["field_id"]
            label = f.get("label") or fid
            p = f.get("selected_param")
            value_str = format_param_value(p)
            unit = get_param_unit(p)
            cond_str = format_condition(p)
            page = p.get("source_page", "") if p else ""
            table_idx = p.get("table_index", "") if p else ""
            row_idx = p.get("row_index", "") if p else ""
            source_hash = p.get("source_hash", "") if p else ""
            source_text = p.get("source_text", "")[:500] if p else ""

            ws.cell(row=row, column=1, value=doc_name)
            ws.cell(row=row, column=2, value=fid)
            ws.cell(row=row, column=3, value=label)
            ws.cell(row=row, column=4, value=status)
            ws.cell(row=row, column=5, value=value_str)
            ws.cell(row=row, column=6, value=unit)
            ws.cell(row=row, column=7, value=cond_str)
            ws.cell(row=row, column=7).alignment = Alignment(wrap_text=True)
            ws.cell(row=row, column=8, value=str(page) if page else "")
            ws.cell(row=row, column=9, value=str(table_idx) if table_idx != "" else "")
            ws.cell(row=row, column=10, value=str(row_idx) if row_idx != "" else "")
            ws.cell(row=row, column=11, value=source_hash)
            ws.cell(row=row, column=12, value=source_text)
            ws.cell(row=row, column=12).alignment = Alignment(wrap_text=True)
            row += 1

    # Column widths
    _set_col_width(ws, 1, 18)  # Document
    _set_col_width(ws, 2, 18)  # Field ID
    _set_col_width(ws, 3, 18)  # Label
    _set_col_width(ws, 4, 18)  # Selection Status
    _set_col_width(ws, 5, 20)  # Value
    _set_col_width(ws, 6, 8)   # Unit
    _set_col_width(ws, 7, 35)  # Condition
    _set_col_width(ws, 8, 6)   # Page
    _set_col_width(ws, 9, 6)   # Table
    _set_col_width(ws, 10, 6)  # Row
    _set_col_width(ws, 11, 16) # Source Hash
    _set_col_width(ws, 12, 70) # Source Text


# =============================================================================
# Main Entry Point
# =============================================================================

def write_excel_report(selection_result: Dict[str, Any], output_path: str) -> None:
    """
    Write Excel report from Final Selector v1 document-based selection result.

    Args:
        selection_result: Document-based selection result from select_final_candidates()
        output_path: Path to output xlsx file
    """
    wb = openpyxl.Workbook()

    default_sheet = wb.active
    wb.remove(default_sheet)

    ws1 = wb.create_sheet("Final Comparison")
    ws2 = wb.create_sheet("Review Needed")
    ws3 = wb.create_sheet("Blocked")
    ws4 = wb.create_sheet("Source Evidence")

    _write_final_comparison(ws1, selection_result)
    _write_review_needed(ws2, selection_result)
    _write_blocked(ws3, selection_result)
    _write_source_evidence(ws4, selection_result)

    wb.save(output_path)
