"""
Excel Output Writer v0

Generates final_comparison.xlsx from Final Selector v1 document-based output.

Sheets:
    1. Final Comparison - final_candidate fields only, per-document columns
    2. Review Needed - review_needed fields with all candidates
    3. Blocked - blocked fields with danger reasons
    4. Source Evidence - source text for all non-missing selections
"""

from typing import Any, Dict, List, Optional

import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter


# =============================================================================
# Helper Functions
# =============================================================================

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

    # Count how many we have
    parts = []
    if min_val is not None:
        parts.append(f"min={min_val}")
    if typ is not None:
        parts.append(f"typ={typ}")
    if max_val is not None:
        parts.append(f"max={max_val}")

    if not parts:
        # Try single value
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
    # Single part
    return parts[0] if parts else (str(val) if val is not None else "")


def get_document_display_name(doc: Dict[str, Any]) -> str:
    """
    Get display name for a document.
    
    Priority: pdf_stem > file_name > document_id prefix.
    """
    pdf_stem = doc.get("pdf_stem") or ""
    file_name = doc.get("file_name") or ""
    doc_id = doc.get("document_id") or ""

    if pdf_stem:
        return pdf_stem
    if file_name:
        return file_name
    if doc_id:
        return doc_id[:8]
    return "unknown"


def _shorten_source_text(text: str, max_len: int = 300) -> str:
    """Shorten source text to max_len, preserve start."""
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


# =============================================================================
# Column Definitions
# =============================================================================

# Final Comparison columns
FINAL_COLS = ["Parameter", "Unit"]  # + one column per document

# Review Needed columns
REVIEW_COLS = [
    "Document", "Field ID", "Label", "Candidate Type",
    "Value", "Unit", "Score", "Reason",
    "Page", "Table", "Row", "Source Text",
]

# Blocked columns
BLOCKED_COLS = [
    "Document", "Field ID", "Label", "Block Reason",
    "Value", "Unit", "Page", "Source Text",
]

# Source Evidence columns
EVIDENCE_COLS = [
    "Document", "Document ID", "Field ID", "Label",
    "Selection Status", "Value", "Unit",
    "Page", "Table", "Row", "Source Hash",
    "Source Text",
]


# =============================================================================
# Sheet Writers
# =============================================================================

def _write_header_row(ws, cols: List[str], row: int = 1) -> None:
    """Write a bold header row."""
    for col_idx, col_name in enumerate(cols, start=1):
        cell = ws.cell(row=row, column=col_idx, value=col_name)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def _auto_width(ws, min_width: int = 10, max_width: int = 50) -> None:
    """Set reasonable column widths based on content."""
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            try:
                cell_len = len(str(cell.value)) if cell.value else 0
                if cell_len > max_len:
                    max_len = cell_len
            except Exception:
                pass
        width = min(max(max_len + 2, min_width), max_width)
        ws.column_dimensions[col_letter].width = width


def _set_text_wrap(ws, col_idx: int) -> None:
    """Enable text wrap for a specific column."""
    col_letter = get_column_letter(col_idx)
    ws.column_dimensions[col_letter].width = 60


def _add_border(ws, row: int, num_cols: int) -> None:
    """Add thin border to a row."""
    thin = Side(border_style="thin", color="AAAAAA")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    for c in range(1, num_cols + 1):
        ws.cell(row=row, column=c).border = border


def _write_final_comparison(ws, selection_result: Dict[str, Any]) -> None:
    """Write Final Comparison sheet (Sheet 1)."""
    docs = selection_result.get("documents", [])

    # Build header: Parameter | Unit | doc1 | doc2 | ...
    header = ["Parameter", "Unit"] + [get_document_display_name(d) for d in docs]
    _write_header_row(ws, header, row=1)
    ws.freeze_panes = "A2"

    # Collect all fields that are final_candidate in at least one document
    all_field_ids = set()
    for doc in docs:
        for f in doc.get("fields", []):
            if f.get("selection_status") == "final_candidate":
                all_field_ids.add(f["field_id"])

    # Build column lookup: doc_idx -> {field_id: field}
    doc_field_map = []
    for doc in docs:
        field_map = {}
        for f in doc.get("fields", []):
            field_map[f["field_id"]] = f
        doc_field_map.append(field_map)

    # Sort fields by their order in target_fields (preserve order from first doc's fields)
    # Use first doc's field order as reference
    if docs and docs[0].get("fields"):
        ordered_fields = [f["field_id"] for f in docs[0]["fields"]]
    else:
        ordered_fields = sorted(all_field_ids)

    row = 2
    for fid in ordered_fields:
        if fid not in all_field_ids:
            continue

        # Get label from first doc that has it
        label = fid
        for dmap in doc_field_map:
            if fid in dmap:
                label = dmap[fid].get("label") or fid
                break

        # Write Parameter cell
        ws.cell(row=row, column=1, value=label)
        ws.cell(row=row, column=1).font = Font(bold=True)

        # Get unit from first doc that has a final_candidate for this field
        unit = ""
        for dmap in doc_field_map:
            if fid in dmap:
                p = dmap[fid].get("selected_param")
                if p:
                    unit = get_param_unit(p)
                    break
        ws.cell(row=row, column=2, value=unit)

        # Write one column per document
        for doc_idx, dmap in enumerate(doc_field_map):
            col = doc_idx + 3  # +3 because col1=Parameter, col2=Unit
            if fid in dmap:
                f = dmap[fid]
                if f.get("selection_status") == "final_candidate":
                    p = f.get("selected_param")
                    value_str = format_param_value(p)
                    ws.cell(row=row, column=col, value=value_str)

                    # Notes: page + score
                    notes_parts = []
                    if p and p.get("source_page"):
                        notes_parts.append(f"p{p['source_page']}")
                    if f.get("selector_score"):
                        notes_parts.append(f"score={f['selector_score']}")
                    if f.get("selector_warnings"):
                        warns = ", ".join(f["selector_warnings"][:2])
                        notes_parts.append(warns[:40])
                    if notes_parts:
                        notes_str = " | ".join(notes_parts)
                        # Write notes in a separate note cell if we had one
                        # For now just leave value - notes can go in a separate column
                        pass
            # else: leave cell empty (not final_candidate)

        row += 1

    # Set column widths
    ws.column_dimensions["A"].width = 20  # Parameter
    ws.column_dimensions["B"].width = 10  # Unit
    for i in range(len(docs)):
        col_letter = get_column_letter(i + 3)
        ws.column_dimensions[col_letter].width = 18


def _write_review_needed(ws, selection_result: Dict[str, Any]) -> None:
    """Write Review Needed sheet (Sheet 2)."""
    _write_header_row(ws, REVIEW_COLS, row=1)
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

            # Primary candidate
            p = f.get("selected_param")
            value_str = format_param_value(p)
            unit = get_param_unit(p)
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
            ws.cell(row=row, column=7, value=score)
            ws.cell(row=row, column=8, value=reason[:200])
            ws.cell(row=row, column=9, value=str(page) if page else "")
            ws.cell(row=row, column=10, value=str(table_idx) if table_idx != "" else "")
            ws.cell(row=row, column=11, value=str(row_idx) if row_idx != "" else "")
            ws.cell(row=row, column=12, value=source_text)

            row += 1

            # Alternative candidates
            for alt in f.get("review_params", []):
                alt_value_str = format_param_value(alt)
                alt_unit = get_param_unit(alt)
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
                ws.cell(row=row, column=7, value="")
                ws.cell(row=row, column=8, value=alt_reason[:200])
                ws.cell(row=row, column=9, value=str(alt_page) if alt_page else "")
                ws.cell(row=row, column=10, value=str(alt_table) if alt_table != "" else "")
                ws.cell(row=row, column=11, value=str(alt_row) if alt_row != "" else "")
                ws.cell(row=row, column=12, value=alt_text)

                row += 1

    # Column widths
    ws.column_dimensions["A"].width = 18  # Document
    ws.column_dimensions["B"].width = 18  # Field ID
    ws.column_dimensions["C"].width = 18  # Label
    ws.column_dimensions["D"].width = 18  # Candidate Type
    ws.column_dimensions["E"].width = 20  # Value
    ws.column_dimensions["F"].width = 8   # Unit
    ws.column_dimensions["G"].width = 8   # Score
    ws.column_dimensions["H"].width = 35  # Reason
    ws.column_dimensions["I"].width = 6   # Page
    ws.column_dimensions["J"].width = 6   # Table
    ws.column_dimensions["K"].width = 6   # Row
    ws.column_dimensions["L"].width = 60  # Source Text
    ws.row_dimensions[row - 1].height = 60


def _write_blocked(ws, selection_result: Dict[str, Any]) -> None:
    """Write Blocked sheet (Sheet 3)."""
    _write_header_row(ws, BLOCKED_COLS, row=1)
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
            page = p.get("source_page", "") if p else ""
            source_text = _shorten_source_text(p.get("source_text", "") if p else "")

            ws.cell(row=row, column=1, value=doc_name)
            ws.cell(row=row, column=2, value=fid)
            ws.cell(row=row, column=3, value=label)
            ws.cell(row=row, column=4, value=reason[:200])
            ws.cell(row=row, column=5, value=value_str)
            ws.cell(row=row, column=6, value=unit)
            ws.cell(row=row, column=7, value=str(page) if page else "")
            ws.cell(row=row, column=8, value=source_text)

            row += 1

    # Column widths
    ws.column_dimensions["A"].width = 18  # Document
    ws.column_dimensions["B"].width = 18  # Field ID
    ws.column_dimensions["C"].width = 18  # Label
    ws.column_dimensions["D"].width = 40  # Block Reason
    ws.column_dimensions["E"].width = 20  # Value
    ws.column_dimensions["F"].width = 8   # Unit
    ws.column_dimensions["G"].width = 6   # Page
    ws.column_dimensions["H"].width = 60  # Source Text


def _write_source_evidence(ws, selection_result: Dict[str, Any]) -> None:
    """Write Source Evidence sheet (Sheet 4)."""
    _write_header_row(ws, EVIDENCE_COLS, row=1)
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
            page = p.get("source_page", "") if p else ""
            table_idx = p.get("table_index", "") if p else ""
            row_idx = p.get("row_index", "") if p else ""
            source_hash = p.get("source_hash", "") if p else ""
            # Keep 300+ chars for evidence
            source_text = p.get("source_text", "")[:500] if p else ""

            ws.cell(row=row, column=1, value=doc_name)
            ws.cell(row=row, column=2, value=doc_id)
            ws.cell(row=row, column=3, value=fid)
            ws.cell(row=row, column=4, value=label)
            ws.cell(row=row, column=5, value=status)
            ws.cell(row=row, column=6, value=value_str)
            ws.cell(row=row, column=7, value=unit)
            ws.cell(row=row, column=8, value=str(page) if page else "")
            ws.cell(row=row, column=9, value=str(table_idx) if table_idx != "" else "")
            ws.cell(row=row, column=10, value=str(row_idx) if row_idx != "" else "")
            ws.cell(row=row, column=11, value=source_hash)
            ws.cell(row=row, column=12, value=source_text)
            ws.cell(row=row, column=12).alignment = Alignment(wrap_text=True)

            row += 1

    # Column widths
    ws.column_dimensions["A"].width = 18  # Document
    ws.column_dimensions["B"].width = 16  # Document ID
    ws.column_dimensions["C"].width = 18  # Field ID
    ws.column_dimensions["D"].width = 18  # Label
    ws.column_dimensions["E"].width = 18  # Selection Status
    ws.column_dimensions["F"].width = 20  # Value
    ws.column_dimensions["G"].width = 8   # Unit
    ws.column_dimensions["H"].width = 6   # Page
    ws.column_dimensions["I"].width = 6   # Table
    ws.column_dimensions["J"].width = 6   # Row
    ws.column_dimensions["K"].width = 16  # Source Hash
    ws.column_dimensions["L"].width = 70  # Source Text


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

    # Remove default sheet
    default_sheet = wb.active
    wb.remove(default_sheet)

    # Create sheets in order
    ws1 = wb.create_sheet("Final Comparison")
    ws2 = wb.create_sheet("Review Needed")
    ws3 = wb.create_sheet("Blocked")
    ws4 = wb.create_sheet("Source Evidence")

    # Write each sheet
    _write_final_comparison(ws1, selection_result)
    _write_review_needed(ws2, selection_result)
    _write_blocked(ws3, selection_result)
    _write_source_evidence(ws4, selection_result)

    # Save
    wb.save(output_path)
