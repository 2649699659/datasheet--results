"""
excel_from_agent.py — Excel generation from Agent 2/3 results

Generates a clean Excel report with:
    1. Final Params — all fields with final/review/blocked/missing status
    2. Consistency Report — Agent 3 cross-parameter check results
    3. Source Evidence — raw source text for traceability

Input:
    - Agent2Result: validated parameters
    - Agent3Result: consistency check report
Output:
    - Excel file (.xlsx)
"""

import re
from typing import Any

import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter

from agent_workflow.contracts import (
    Agent2Result,
    Agent3Result,
    FieldStatus,
    ConsistencyCheck,
)


# ─────────────────────────────────────────────────────────────────────────────
# Styling helpers
# ─────────────────────────────────────────────────────────────────────────────

HEADER_FILL = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
FINAL_FILL = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
REVIEW_FILL = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
BLOCKED_FILL = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
MISSING_FILL = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")
PASS_FILL = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
FAIL_FILL = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
WARN_FILL = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
SKIP_FILL = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")

THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)


def _header_cell(ws, row: int, col: int, value: str, width: float | None = None):
    cell = ws.cell(row=row, column=col, value=value)
    cell.font = HEADER_FONT
    cell.fill = HEADER_FILL
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = THIN_BORDER
    if width is not None:
        ws.column_dimensions[get_column_letter(col)].width = width
    return cell


def _data_cell(ws, row: int, col: int, value: Any, fill: PatternFill | None = None, bold: bool = False):
    cell = ws.cell(row=row, column=col, value=value)
    cell.alignment = Alignment(vertical="center", wrap_text=True)
    cell.border = THIN_BORDER
    if fill:
        cell.fill = fill
    if bold:
        cell.font = Font(bold=True)
    return cell


def _format_value(param) -> str:
    """Format parameter value as a clean string."""
    parts = []
    for key in ("min", "typ", "max", "value"):
        v = getattr(param, key, None)
        if v is not None:
            parts.append(f"{key}={v}")
    if not parts:
        return "-"
    return ", ".join(parts)


def _normalize_condition(text: str) -> str:
    """Normalize condition text for readability."""
    if not text:
        return ""
    # Fix split keys
    for pattern, replacement in [
        (r"\bV\s*G\s*S\b", "VGS"),
        (r"\bV\s*D\s*S\b", "VDS"),
        (r"\bV\s*D\s*D\b", "VDD"),
        (r"\bI\s*D\b", "ID"),
        (r"\bI\s*F\b", "IF"),
        (r"\bT\s*C\b", "TC"),
        (r"\bR\s*G\b", "RG"),
    ]:
        text = re.sub(pattern, replacement, text)
    # Normalize micro sign
    text = text.replace("\u00b5", "μ")
    return text.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Sheet 1: Final Params
# ─────────────────────────────────────────────────────────────────────────────

def _write_final_params(ws, agent2: Agent2Result):
    """Write the Final Params sheet."""
    ws.title = "Final Params"

    # Headers
    headers = [
        "Field ID", "Status", "Value", "Min", "Typ", "Max", "Unit",
        "Condition", "Confidence", "Source Page", "Table", "Row",
        "Source Text", "Reason", "Warnings",
    ]
    widths = [20, 14, 18, 10, 10, 10, 8, 30, 12, 12, 8, 8, 50, 40, 30]

    for col, (h, w) in enumerate(zip(headers, widths), 1):
        _header_cell(ws, 1, col, h, w)

    ws.row_dimensions[1].height = 30

    # Sort: final first, then review, blocked, missing
    STATUS_ORDER = {FieldStatus.FINAL: 0, FieldStatus.REVIEW_NEEDED: 1, FieldStatus.BLOCKED: 2, FieldStatus.MISSING: 3}

    def status_sort_key(p):
        s = p.status if isinstance(p.status, FieldStatus) else FieldStatus(p.status)
        return STATUS_ORDER.get(s, 99)

    sorted_params = sorted(agent2.final_params, key=status_sort_key)

    for ri, param in enumerate(sorted_params, 2):
        status_str = param.status.value if isinstance(param.status, FieldStatus) else str(param.status)

        fill = {
            "final": FINAL_FILL,
            "review_needed": REVIEW_FILL,
            "blocked": BLOCKED_FILL,
            "missing": MISSING_FILL,
        }.get(status_str)

        ws.row_dimensions[ri].height = 22

        _data_cell(ws, ri, 1, param.field_id, fill, bold=True)
        _data_cell(ws, ri, 2, status_str, fill)
        _data_cell(ws, ri, 3, _format_value(param), fill)
        _data_cell(ws, ri, 4, param.min, fill)
        _data_cell(ws, ri, 5, param.typ, fill)
        _data_cell(ws, ri, 6, param.max, fill)
        _data_cell(ws, ri, 7, param.unit or "", fill)
        _data_cell(ws, ri, 8, _normalize_condition(param.condition or ""), fill)
        _data_cell(ws, ri, 9, f"{param.confidence:.2f}" if param.confidence else "-", fill)
        _data_cell(ws, ri, 10, param.source_page, fill)
        _data_cell(ws, ri, 11, param.table_index, fill)
        _data_cell(ws, ri, 12, param.row_index, fill)
        _data_cell(ws, ri, 13, _normalize_condition(param.source_text or "")[:300], fill)
        _data_cell(ws, ri, 14, param.reason[:200] if param.reason else "", fill)
        _data_cell(ws, ri, 15, "; ".join(param.warnings)[:200] if param.warnings else "", fill)

    # Summary row
    summary_row = len(sorted_params) + 3
    ws.cell(row=summary_row, column=1, value="Summary").font = Font(bold=True)
    ws.cell(row=summary_row + 1, column=1, value=f"Manufacturer: {agent2.manufacturer or 'missing'}")
    ws.cell(row=summary_row + 2, column=1, value=f"Document: {agent2.document_id}")
    ws.cell(row=summary_row + 3, column=1, value=f"Total fields: {len(sorted_params)}")
    ws.cell(row=summary_row + 4, column=1, value=f"Final: {sum(1 for p in sorted_params if (p.status.value if isinstance(p.status, FieldStatus) else str(p.status)) == 'final')}")
    ws.cell(row=summary_row + 5, column=1, value=f"Review Needed: {sum(1 for p in sorted_params if (p.status.value if isinstance(p.status, FieldStatus) else str(p.status)) == 'review_needed')}")
    ws.cell(row=summary_row + 6, column=1, value=f"Blocked: {sum(1 for p in sorted_params if (p.status.value if isinstance(p.status, FieldStatus) else str(p.status)) == 'blocked')}")
    ws.cell(row=summary_row + 7, column=1, value=f"Missing: {sum(1 for p in sorted_params if (p.status.value if isinstance(p.status, FieldStatus) else str(p.status)) == 'missing')}")


# ─────────────────────────────────────────────────────────────────────────────
# Sheet 2: Consistency Report
# ─────────────────────────────────────────────────────────────────────────────

def _write_consistency_report(ws, agent3: Agent3Result):
    """Write the Consistency Report sheet."""
    ws.title = "Consistency Report"

    headers = ["Rule ID", "Rule Name", "Severity", "Status", "Verdict", "Suggested Action", "Details", "Fields"]
    widths = [30, 25, 12, 12, 50, 18, 40, 30]

    for col, (h, w) in enumerate(zip(headers, widths), 1):
        _header_cell(ws, 1, col, h, w)

    ws.row_dimensions[1].height = 30

    def status_fill(status: str) -> PatternFill:
        return {"pass": PASS_FILL, "fail": FAIL_FILL, "warning": WARN_FILL, "skipped": SKIP_FILL}.get(status, MISSING_FILL)

    for ri, check in enumerate(agent3.consistency_checks, 2):
        ws.row_dimensions[ri].height = 30
        fill = status_fill(check.status)

        _data_cell(ws, ri, 1, check.rule_id, fill, bold=True)
        _data_cell(ws, ri, 2, check.rule_name, fill)
        _data_cell(ws, ri, 3, check.severity, fill)
        _data_cell(ws, ri, 4, check.status, fill)
        _data_cell(ws, ri, 5, check.verdict, fill)
        _data_cell(ws, ri, 6, check.suggested_action, fill)

        # Details as formatted string
        details_str = "; ".join(f"{k}={v}" for k, v in check.details.items())
        _data_cell(ws, ri, 7, details_str, fill)

        _data_cell(ws, ri, 8, ", ".join(check.fields_involved), fill)

    # Summary
    s = agent3.summary
    summary_row = len(agent3.consistency_checks) + 3
    ws.cell(row=summary_row, column=1, value="Summary").font = Font(bold=True)
    ws.cell(row=summary_row + 1, column=1, value=f"Total: {s.get('total_checks', 0)}")
    ws.cell(row=summary_row + 2, column=1, value=f"Passed: {s.get('passed', 0)}")
    ws.cell(row=summary_row + 3, column=1, value=f"Warnings: {s.get('warnings', 0)}")
    ws.cell(row=summary_row + 4, column=1, value=f"Failed: {s.get('failed', 0)}")
    ws.cell(row=summary_row + 5, column=1, value=f"Skipped: {s.get('skipped', 0)}")

    if agent3.recommendations:
        ws.cell(row=summary_row + 7, column=1, value="Recommendations").font = Font(bold=True)
        for ri, rec in enumerate(agent3.recommendations, summary_row + 8):
            ws.cell(row=ri, column=1, value=rec)


# ─────────────────────────────────────────────────────────────────────────────
# Sheet 3: Field Detail
# ─────────────────────────────────────────────────────────────────────────────

def _write_field_detail(ws, agent2: Agent2Result):
    """Write a field-by-field detail sheet."""
    ws.title = "Field Detail"

    headers = ["#", "Field ID", "Status", "Min", "Typ", "Max", "Unit", "Condition", "Confidence", "Reason", "Missing Reason"]
    widths = [6, 22, 14, 12, 12, 12, 8, 40, 12, 50, 25]

    for col, (h, w) in enumerate(zip(headers, widths), 1):
        _header_cell(ws, 1, col, h, w)

    ws.row_dimensions[1].height = 30

    for ri, param in enumerate(agent2.final_params, 2):
        status_str = param.status.value if isinstance(param.status, FieldStatus) else str(param.status)
        fill = {"final": FINAL_FILL, "review_needed": REVIEW_FILL, "blocked": BLOCKED_FILL, "missing": MISSING_FILL}.get(status_str)

        # Build reason text
        reason_text = param.reason[:150] if param.reason else ""
        if status_str == "missing" and param.missing_reason:
            reason_text = f"[{param.missing_reason}] {reason_text}".strip()

        ws.row_dimensions[ri].height = 22
        _data_cell(ws, ri, 1, ri - 1, fill)
        _data_cell(ws, ri, 2, param.field_id, fill, bold=True)
        _data_cell(ws, ri, 3, status_str, fill)
        _data_cell(ws, ri, 4, param.min, fill)
        _data_cell(ws, ri, 5, param.typ, fill)
        _data_cell(ws, ri, 6, param.max, fill)
        _data_cell(ws, ri, 7, param.unit or "", fill)
        _data_cell(ws, ri, 8, _normalize_condition(param.condition or "")[:80], fill)
        _data_cell(ws, ri, 9, f"{param.confidence:.2f}" if param.confidence else "-", fill)
        _data_cell(ws, ri, 10, reason_text, fill)
        _data_cell(ws, ri, 11, param.missing_reason if status_str == "missing" and param.missing_reason else "", fill)


# ─────────────────────────────────────────────────────────────────────────────
# Sheet 4: All Parameters (Phase 5)
# ─────────────────────────────────────────────────────────────────────────────

def _write_all_parameters(ws, inventory_records: list):
    """Write the All Parameters sheet from inventory records."""
    ws.title = "All Parameters"

    # Headers
    headers = [
        "Page", "Table", "Row", "Section", "Symbol", "Parameter",
        "Value", "Min", "Typ", "Max", "Unit", "Condition",
        "Schema Type", "Mapping Status", "Canonical Field ID",
        "Extraction Status", "Source Text", "Quality Flags",
    ]
    widths = [8, 8, 8, 25, 15, 30, 12, 10, 10, 10, 10, 35, 15, 15, 20, 18, 50, 30]

    for col, (h, w) in enumerate(zip(headers, widths), 1):
        _header_cell(ws, 1, col, h, w)

    ws.row_dimensions[1].height = 30

    for ri, record in enumerate(inventory_records, 2):
        ws.row_dimensions[ri].height = 22
        _data_cell(ws, ri, 1, record.page_number)
        _data_cell(ws, ri, 2, record.table_index)
        _data_cell(ws, ri, 3, record.row_index)
        _data_cell(ws, ri, 4, record.section_title or "")
        _data_cell(ws, ri, 5, record.symbol or "")
        _data_cell(ws, ri, 6, record.parameter_name or "")
        _data_cell(ws, ri, 7, record.value)
        _data_cell(ws, ri, 8, record.min)
        _data_cell(ws, ri, 9, record.typ)
        _data_cell(ws, ri, 10, record.max)
        _data_cell(ws, ri, 11, record.unit or "")
        _data_cell(ws, ri, 12, _normalize_condition(record.resolved_condition or "")[:80])
        _data_cell(ws, ri, 13, record.source_schema_type or "")
        _data_cell(ws, ri, 14, record.mapping_status.value if hasattr(record.mapping_status, 'value') else str(record.mapping_status))
        _data_cell(ws, ri, 15, record.canonical_field_id or "")
        _data_cell(ws, ri, 16, record.extraction_status.value if hasattr(record.extraction_status, 'value') else str(record.extraction_status))
        _data_cell(ws, ri, 17, _normalize_condition(record.source_text or "")[:200])
        _data_cell(ws, ri, 18, "; ".join(record.quality_flags) if record.quality_flags else "")

    # Summary
    summary_row = len(inventory_records) + 3
    ws.cell(row=summary_row, column=1, value="Summary").font = Font(bold=True)
    ws.cell(row=summary_row + 1, column=1, value=f"Total Parameters: {len(inventory_records)}")


# ─────────────────────────────────────────────────────────────────────────────
# Sheet 5: Unmapped Parameters (Phase 5)
# ─────────────────────────────────────────────────────────────────────────────

def _write_unmapped_parameters(ws, inventory_records: list):
    """Write the Unmapped Parameters sheet."""
    ws.title = "Unmapped Parameters"

    # Filter to only unmapped records
    unmapped = [r for r in inventory_records if (
        (hasattr(r.mapping_status, 'value') and r.mapping_status.value == 'unmapped') or
        (isinstance(r.mapping_status, str) and r.mapping_status == 'unmapped')
    )]

    # Headers
    headers = [
        "Page", "Table", "Row", "Section", "Symbol", "Parameter",
        "Value", "Min", "Typ", "Max", "Unit", "Condition",
        "Schema Type", "Source Text",
    ]
    widths = [8, 8, 8, 25, 15, 30, 12, 10, 10, 10, 10, 35, 15, 50]

    for col, (h, w) in enumerate(zip(headers, widths), 1):
        _header_cell(ws, 1, col, h, w)

    ws.row_dimensions[1].height = 30

    for ri, record in enumerate(unmapped, 2):
        ws.row_dimensions[ri].height = 22
        _data_cell(ws, ri, 1, record.page_number)
        _data_cell(ws, ri, 2, record.table_index)
        _data_cell(ws, ri, 3, record.row_index)
        _data_cell(ws, ri, 4, record.section_title or "")
        _data_cell(ws, ri, 5, record.symbol or "")
        _data_cell(ws, ri, 6, record.parameter_name or "")
        _data_cell(ws, ri, 7, record.value)
        _data_cell(ws, ri, 8, record.min)
        _data_cell(ws, ri, 9, record.typ)
        _data_cell(ws, ri, 10, record.max)
        _data_cell(ws, ri, 11, record.unit or "")
        _data_cell(ws, ri, 12, _normalize_condition(record.resolved_condition or "")[:80])
        _data_cell(ws, ri, 13, record.source_schema_type or "")
        _data_cell(ws, ri, 14, _normalize_condition(record.source_text or "")[:200])

    # Summary
    summary_row = len(unmapped) + 3
    ws.cell(row=summary_row, column=1, value="Summary").font = Font(bold=True)
    ws.cell(row=summary_row + 1, column=1, value=f"Unmapped Parameters: {len(unmapped)}")


# ─────────────────────────────────────────────────────────────────────────────
# Sheet 6: Inventory Needs Review (Phase 5)
# ─────────────────────────────────────────────────────────────────────────────

def _write_needs_review(ws, inventory_records: list):
    """Write the Inventory Needs Review sheet."""
    ws.title = "Needs Review"

    # Filter to needs_review records (UNKNOWN but looks like parameter)
    needs_review = [r for r in inventory_records if (
        (hasattr(r.mapping_status, 'value') and r.mapping_status.value == 'needs_review') or
        (isinstance(r.mapping_status, str) and r.mapping_status == 'needs_review')
    )]

    # Headers
    headers = [
        "Page", "Table", "Row", "Section", "Symbol", "Parameter",
        "Value", "Min", "Typ", "Max", "Unit", "Condition",
        "Schema Type", "Source Text",
    ]
    widths = [8, 8, 8, 25, 15, 30, 12, 10, 10, 10, 10, 35, 15, 50]

    for col, (h, w) in enumerate(zip(headers, widths), 1):
        _header_cell(ws, 1, col, h, w)

    ws.row_dimensions[1].height = 30

    for ri, record in enumerate(needs_review, 2):
        ws.row_dimensions[ri].height = 22
        _data_cell(ws, ri, 1, record.page_number)
        _data_cell(ws, ri, 2, record.table_index)
        _data_cell(ws, ri, 3, record.row_index)
        _data_cell(ws, ri, 4, record.section_title or "")
        _data_cell(ws, ri, 5, record.symbol or "")
        _data_cell(ws, ri, 6, record.parameter_name or "")
        _data_cell(ws, ri, 7, record.value)
        _data_cell(ws, ri, 8, record.min)
        _data_cell(ws, ri, 9, record.typ)
        _data_cell(ws, ri, 10, record.max)
        _data_cell(ws, ri, 11, record.unit or "")
        _data_cell(ws, ri, 12, _normalize_condition(record.resolved_condition or "")[:80])
        _data_cell(ws, ri, 13, record.source_schema_type or "")
        _data_cell(ws, ri, 14, _normalize_condition(record.source_text or "")[:200])

    # Summary
    summary_row = len(needs_review) + 3
    ws.cell(row=summary_row, column=1, value="Summary").font = Font(bold=True)
    ws.cell(row=summary_row + 1, column=1, value=f"Needs Review Parameters: {len(needs_review)}")


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def write_excel_from_agent(
    agent2: Agent2Result,
    agent3: Agent3Result,
    output_path: str,
    inventory_records: list | None = None,
) -> None:
    """
    Write Excel report from Agent 2/3 results.

    Args:
        agent2: Agent2Result from Step 2
        agent3: Agent3Result from Step 3
        output_path: Path to output .xlsx file
        inventory_records: Optional list of ParameterRecord for Phase 5
    """
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # Remove default sheet

    _write_final_params(wb.create_sheet("Final Params"), agent2)
    _write_consistency_report(wb.create_sheet("Consistency"), agent3)
    _write_field_detail(wb.create_sheet("Field Detail"), agent2)

    # Phase 5: Add Parameter Inventory sheets
    if inventory_records:
        _write_all_parameters(wb.create_sheet("All Parameters"), inventory_records)
        _write_unmapped_parameters(wb.create_sheet("Unmapped"), inventory_records)
        _write_needs_review(wb.create_sheet("Needs Review"), inventory_records)

    wb.save(output_path)
