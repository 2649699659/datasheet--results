"""
enricher.py — Conversion from CamelotPayload to EnrichedPayload.

Phase 1: Lossless conversion with row-level classification.
Phase 2A: Adds table/section title tracking and temperature condition resolution.

No LLM calls. No external API keys. No file I/O.
"""

import copy
from typing import Any

from ..contracts import CamelotPayload, CamelotPage, CamelotTable, CamelotTableRow
from .models import (
    EnrichedPayload,
    EnrichedPage,
    EnrichedTable,
    EnrichedRow,
    RowType,
    ContextStatus,
)
from .row_classifier import RowClassifier
from .heading_parser import (
    parse_temperature_from_text,
    extract_temperature_from_cells,
    extract_raw_condition_from_cells,
    extract_condition_from_heading,
)


# ─────────────────────────────────────────────────────────────────────────────
# Main conversion
# ─────────────────────────────────────────────────────────────────────────────

def enrich_payload(payload: CamelotPayload) -> EnrichedPayload:
    """
    Convert a CamelotPayload into an EnrichedPayload.

    Phase 1: Lossless conversion with row-level classification.
    Phase 2A: Adds table/section title tracking, temperature condition
    resolution, and heading condition propagation.

    Args:
        payload: CamelotPayload from Step 0.

    Returns:
        EnrichedPayload with enriched rows.
    """
    classifier = RowClassifier()

    enriched_pages: list[EnrichedPage] = []

    for page in payload.pages:
        enriched_tables: list[EnrichedTable] = []

        for table in page.tables:
            enriched_rows: list[EnrichedRow] = []

            # ── Phase 2A: Context tracking per table ─────────────────────────
            current_table_title: str | None = None
            current_section_title: str | None = None
            current_default_conditions: dict[str, str] = {}

            for row in table.rows:
                # Deep copy cells to ensure raw_cells is independent from original
                cells_copy = _deep_copy_cells(row.cells)

                # Phase 1: Classify the row
                row_type = classifier.classify(cells_copy)

                # Generate stable row_id
                row_id = _make_row_id(
                    page_number=table.page_number,
                    table_index=table.table_index,
                    row_index=row.row_index,
                )

                # ── Phase 2A: Context tracking ─────────────────────────────
                (
                    current_table_title,
                    current_section_title,
                    current_default_conditions,
                    enriched_row,
                ) = _process_row(
                    row=row,
                    cells_copy=cells_copy,
                    row_id=row_id,
                    row_type=row_type,
                    page_number=table.page_number,
                    table_index=table.table_index,
                    current_table_title=current_table_title,
                    current_section_title=current_section_title,
                    current_default_conditions=current_default_conditions,
                )

                enriched_rows.append(enriched_row)

            enriched_table = EnrichedTable(
                page_number=table.page_number,
                table_index=table.table_index,
                flavor=table.flavor,
                rows=enriched_rows,
                accuracy=table.accuracy,
                whitespace=table.whitespace,
                score=getattr(table, 'score', 0.0),
                table_title=None,   # Phase 2A: populated per row
            )
            enriched_tables.append(enriched_table)

        enriched_page = EnrichedPage(
            page_number=page.page_number,
            tables=enriched_tables,
        )
        enriched_pages.append(enriched_page)

    enriched_payload = EnrichedPayload(
        document_id=payload.document_id,
        file_name=payload.file_name,
        pdf_path=payload.pdf_path,
        source_backend=payload.source_backend,
        pages=enriched_pages,
        enriched_row_count=0,
        row_type_counts={},
        table_titles_detected=[],
        section_titles_detected=[],
        heading_conditions_parsed=0,
        heading_conditions_applied=0,
        heading_condition_overrides=0,
        ambiguous_title_rows=[],
    )
    enriched_payload._recompute_stats()

    return enriched_payload


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2A: Row processing
# ─────────────────────────────────────────────────────────────────────────────

def _process_row(
    row: CamelotTableRow,
    cells_copy: list[str],
    row_id: str,
    row_type: RowType,
    page_number: int,
    table_index: int,
    current_table_title: str | None,
    current_section_title: str | None,
    current_default_conditions: dict[str, str],
) -> tuple[
    str | None,  # updated current_table_title
    str | None,  # updated current_section_title
    dict[str, str],  # updated current_default_conditions
    EnrichedRow,
]:
    """
    Process a single row and update context.

    Returns:
        (new_table_title, new_section_title, new_default_conditions, enriched_row)
    """
    new_table_title = current_table_title
    new_section_title = current_section_title
    new_default_conditions = dict(current_default_conditions)

    # Join all cells for pattern matching (handles Camelot-split cells)
    joined_all = " ".join(c for c in cells_copy if c.strip())

    # ── Section Title rows ──────────────────────────────────────────────────
    if row_type == RowType.SECTION_TITLE:
        new_section_title = joined_all or None
        new_default_conditions = {}

        # Extract temperature condition from section heading
        heading_temp = extract_condition_from_heading(joined_all)
        if heading_temp:
            new_default_conditions.update(heading_temp)

        enriched_row = EnrichedRow(
            row_id=row_id,
            page_number=page_number,
            table_index=table_index,
            row_index=row.row_index,
            raw_cells=cells_copy,
            row_type=row_type,
            table_title=current_table_title,   # inherit from context
            section_title=new_section_title,
            raw_condition=None,
            resolved_condition=None,
            default_conditions=dict(new_default_conditions),
            condition_sources={"row": None, "table_heading": None},
            context_status=ContextStatus.UNCHANGED,
            quality_flags=[],
        )
        return new_table_title, new_section_title, new_default_conditions, enriched_row

    # ── Table Title rows ────────────────────────────────────────────────────
    if row_type == RowType.TABLE_TITLE:
        new_table_title = joined_all or None
        # New table_title resets section context
        new_section_title = None
        new_default_conditions = {}

        # Extract temperature condition from table heading (e.g., "at TC=25°C...")
        heading_temp = extract_condition_from_heading(joined_all)
        if heading_temp:
            new_default_conditions.update(heading_temp)

        enriched_row = EnrichedRow(
            row_id=row_id,
            page_number=page_number,
            table_index=table_index,
            row_index=row.row_index,
            raw_cells=cells_copy,
            row_type=row_type,
            table_title=new_table_title,
            section_title=None,
            raw_condition=None,
            resolved_condition=None,
            default_conditions=dict(new_default_conditions),
            condition_sources={"row": None, "table_heading": None},
            context_status=ContextStatus.UNCHANGED,
            quality_flags=[],
        )
        return new_table_title, new_section_title, new_default_conditions, enriched_row

    # ── Column Header, Empty, Separator, Unknown rows ───────────────────────
    # These do NOT update context
    if row_type in (
        RowType.COLUMN_HEADER,
        RowType.EMPTY,
        RowType.SEPARATOR,
        RowType.UNKNOWN,
    ):
        enriched_row = EnrichedRow(
            row_id=row_id,
            page_number=page_number,
            table_index=table_index,
            row_index=row.row_index,
            raw_cells=cells_copy,
            row_type=row_type,
            table_title=current_table_title,
            section_title=current_section_title,
            raw_condition=None,
            resolved_condition=None,
            default_conditions={},
            condition_sources={"row": None, "table_heading": None},
            context_status=ContextStatus.UNCHANGED,
            quality_flags=[],
        )
        return new_table_title, new_section_title, new_default_conditions, enriched_row

    # ── Parameter rows ──────────────────────────────────────────────────────
    # These inherit current context and resolve conditions
    if row_type == RowType.PARAMETER:
        enriched_row = _resolve_parameter_row(
            row_id=row_id,
            page_number=page_number,
            table_index=table_index,
            row_index=row.row_index,
            cells_copy=cells_copy,
            current_table_title=current_table_title,
            current_section_title=current_section_title,
            current_default_conditions=current_default_conditions,
        )
        # Parameter rows do NOT update context
        return new_table_title, new_section_title, new_default_conditions, enriched_row

    # ── Fallback: unknown row type ─────────────────────────────────────────
    enriched_row = EnrichedRow(
        row_id=row_id,
        page_number=page_number,
        table_index=table_index,
        row_index=row.row_index,
        raw_cells=cells_copy,
        row_type=row_type,
        table_title=current_table_title,
        section_title=current_section_title,
        raw_condition=None,
        resolved_condition=None,
        default_conditions={},
        condition_sources={"row": None, "table_heading": None},
        context_status=ContextStatus.UNCHANGED,
        quality_flags=[],
    )
    return new_table_title, new_section_title, new_default_conditions, enriched_row


def _resolve_parameter_row(
    row_id: str,
    page_number: int,
    table_index: int,
    row_index: int,
    cells_copy: list[str],
    current_table_title: str | None,
    current_section_title: str | None,
    current_default_conditions: dict[str, str],
) -> EnrichedRow:
    """
    Resolve conditions for a parameter row.

    Priority:
    1. Row's own temperature condition (if present)
    2. Heading/section default temperature (if no row-level temp)

    Condition sources tracks where each condition came from.
    """
    quality_flags: list[str] = []
    condition_sources: dict[str, str | None] = {"row": None, "table_heading": None}
    resolved_conditions: dict[str, str] = {}

    # Extract temperature from the row's own condition cell
    row_temp = extract_temperature_from_cells(cells_copy)

    # Extract raw condition string
    raw_condition = extract_raw_condition_from_cells(cells_copy)

    if row_temp:
        # Row has its own temperature → use it, override heading
        resolved_conditions.update(row_temp)
        condition_sources["row"] = str(row_temp)
        if current_default_conditions:
            quality_flags.append("heading_condition_overridden_by_row")
            condition_sources["table_heading"] = str(current_default_conditions)
    elif current_default_conditions:
        # Row has no temperature, use heading default
        resolved_conditions.update(current_default_conditions)
        condition_sources["row"] = None
        condition_sources["table_heading"] = str(current_default_conditions)

    # Build resolved_condition string from resolved conditions
    resolved_condition_str = None
    if resolved_conditions:
        parts = [f"{k}={v}" for k, v in resolved_conditions.items()]
        resolved_condition_str = "; ".join(parts)

    context_status = ContextStatus.RESOLVED if resolved_conditions else ContextStatus.UNCHANGED

    return EnrichedRow(
        row_id=row_id,
        page_number=page_number,
        table_index=table_index,
        row_index=row_index,
        raw_cells=cells_copy,
        row_type=RowType.PARAMETER,
        table_title=current_table_title,
        section_title=current_section_title,
        raw_condition=raw_condition,
        resolved_condition=resolved_condition_str,
        default_conditions=dict(resolved_conditions),
        condition_sources=condition_sources,
        context_status=context_status,
        quality_flags=quality_flags,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────────────

def _make_row_id(page_number: int, table_index: int, row_index: int) -> str:
    """Generate a stable, deterministic row ID."""
    return f"p{page_number}_t{table_index}_r{row_index}"


def _deep_copy_cells(cells: list[str]) -> list[str]:
    """Deep copy a list of cell strings."""
    return [str(c) for c in cells]


# ─────────────────────────────────────────────────────────────────────────────
# Dict-based conversion (for loading from JSON)
# ─────────────────────────────────────────────────────────────────────────────

def enrich_payload_from_dict(d: dict) -> EnrichedPayload:
    """
    Convert a CamelotPayload dict (not CamelotPayload object) to EnrichedPayload.

    This is used when loading a CamelotPayload from JSON before enrichment.
    """
    payload = CamelotPayload.from_dict(d)
    return enrich_payload(payload)
