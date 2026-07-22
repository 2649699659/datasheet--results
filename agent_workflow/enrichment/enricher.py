"""
enricher.py — Conversion from CamelotPayload to EnrichedPayload.

Phase 1: Lossless conversion with row-level classification.
Phase 2A: Adds table/section title tracking and temperature condition resolution.
Phase 2B: Resolves page-level headings outside Camelot table boundaries.

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
from .shared_condition_propagator import _has_meaningful_test_conditions
from .row_classifier import RowClassifier
from .heading_parser import (
    parse_temperature_from_text,
    extract_temperature_from_cells,
    extract_raw_condition_from_cells,
    extract_condition_from_heading,
)
from .page_heading_resolver import (
    resolve_page_headings,
    get_table_page_heading,
)
from .shared_condition_propagator import (
    propagate_shared_conditions,
    apply_propagation_to_source,
)
from .manufacturer_detector import extract_manufacturer
from .condition_resolver import (
    RowConditionContext,
    ConditionLayer,
    resolve_condition_context,
    apply_resolved_condition_to_row,
)


# ─────────────────────────────────────────────────────────────────────────────
# Main conversion
# ─────────────────────────────────────────────────────────────────────────────

def enrich_payload(
    payload: CamelotPayload,
    pdf_path: str | None = None,
) -> EnrichedPayload:
    """
    Convert a CamelotPayload into an EnrichedPayload.

    Phase 1: Lossless conversion with row-level classification.
    Phase 2A: Adds table/section title tracking, temperature condition
              resolution, and heading condition propagation.
    Phase 2B (requires pdf_path): Resolves page-level headings outside
              Camelot table boundaries and applies them to tables without
              table-level section headings.

    Args:
        payload: CamelotPayload from Step 0.
        pdf_path: Path to the PDF file (required for Phase 2B page heading resolution).

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
        schema_version="1.0",
        source_fingerprint=payload.source_fingerprint.to_dict() if payload.source_fingerprint else None,
        enriched_row_count=0,
        row_type_counts={},
        table_titles_detected=[],
        section_titles_detected=[],
        heading_conditions_parsed=0,
        heading_conditions_applied=0,
        heading_condition_overrides=0,
        ambiguous_title_rows=[],
    )

    # ── Phase 2B: Page-level heading resolution ───────────────────────────
    # Requires pdf_path and table_bbox in payload (from updated Step 0).
    # Runs after Phase 2A, applying page-level headings only to tables
    # that do NOT have a section_title from Phase 2A.
    if pdf_path is not None:
        _apply_page_headings(enriched_payload, payload, pdf_path)

    # ── Phase 3A: Shared condition propagation ─────────────────────────────
    # Propagates shared test conditions to contiguous PARAMETER rows
    # within the same table and section. Does NOT require pdf_path.
    apply_shared_condition_propagation(enriched_payload)

    # ── Phase 3B: Document-level manufacturer extraction ───────────────────
    # Extracts manufacturer from document-level text (page text, not table rows).
    # Does NOT modify any row data. Requires pdf_path.
    if pdf_path is not None:
        manufacturer_result = extract_manufacturer(pdf_path)
        enriched_payload.document_metadata = {
            "manufacturer": manufacturer_result.to_dict()
        }

    # ── Final Resolver Pass: Generate resolved_condition from condition layers ─
    # After all enrichment phases are complete, run the unified resolver on each row
    # to generate resolved_condition from the condition layers (raw, shared_group,
    # table_default, page_default).
    _resolve_all_row_conditions(enriched_payload)

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

    Now uses condition layers instead of directly setting resolved_condition:
    - raw layer: conditions from the row's own cells
    - table_default layer: temperature from section heading

    The final resolved_condition is generated by the unified resolver after all phases.
    """
    quality_flags: list[str] = []
    condition_sources: dict[str, str | None] = {"row": None, "table_heading": None}

    # Extract temperature from the row's own condition cell
    row_temp = extract_temperature_from_cells(cells_copy)

    # Extract raw condition string (full condition text from cells)
    raw_condition = extract_raw_condition_from_cells(cells_copy)

    # Parse raw_condition into key-value pairs for the raw layer
    raw_values: dict[str, str] = {}
    if raw_condition:
        # Parse the condition string
        from .condition_resolver import _parse_condition_str
        raw_values = _parse_condition_str(raw_condition)

    # Add row's own temperature to raw layer (if present)
    if row_temp:
        raw_values.update(row_temp)
        if current_default_conditions:
            quality_flags.append("heading_condition_overridden_by_row")

    # Initialize condition_context with raw layer
    condition_context = RowConditionContext(
        raw=ConditionLayer(
            values=dict(raw_values),
            source_row_ids=[row_id],
            evidence_type="raw_row_condition",
        ),
        table_default=ConditionLayer(
            values={},  # Will be set by Phase 2A
            source_row_ids=[],
            evidence_type="table_heading",
        ),
        page_default=ConditionLayer(),
        shared_group=ConditionLayer(),
    )

    # If row has no temperature from cells but has heading default,
    # write the heading temperature to table_default layer
    if not row_temp and current_default_conditions:
        condition_context.table_default.values.update(current_default_conditions)
        condition_context.table_default.source_row_ids = [row_id]
        condition_sources["table_heading"] = str(current_default_conditions)
    elif row_temp and current_default_conditions:
        # Row has its own temperature, but still record heading default
        condition_sources["table_heading"] = str(current_default_conditions)

    # resolved_condition will be generated by the unified resolver
    resolved_condition_str = None
    context_status = ContextStatus.RESOLVED if (raw_values or condition_context.table_default.values) else ContextStatus.UNCHANGED

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
        resolved_condition=resolved_condition_str,  # Will be set by final resolver
        default_conditions=dict(current_default_conditions) if current_default_conditions else {},
        condition_sources=condition_sources,
        condition_context=condition_context,
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
# Phase 2B: Page-level heading application
# ─────────────────────────────────────────────────────────────────────────────

def _apply_page_headings(
    enriched_payload: EnrichedPayload,
    camelot_payload: CamelotPayload,
    pdf_path: str,
) -> None:
    """
    Apply page-level headings to tables that don't have section titles from Phase 2A.

    Phase 2B identifies page-level headings (outside Camelot table boundaries) and
    applies them only to tables that did NOT get a section_title from Phase 2A.

    This resolves the case where section headings like "Body Diode Characteristics"
    appear outside the Camelot table (above the table) and are not captured by
    Phase 2A's within-table row processing.
    """
    # Resolve page headings using the CamelotPayload (has table_bbox)
    page_results = resolve_page_headings(camelot_payload, pdf_path)

    for ep in enriched_payload.pages:
        page_num = ep.page_number
        if page_num not in page_results:
            continue
        result = page_results[page_num]

        for et in ep.tables:
            table_idx = et.table_index

            # Check if this table already has a section_title from Phase 2A
            has_phase2a_section = any(
                row.section_title is not None
                for row in et.rows
                if row.row_type == RowType.PARAMETER
            )
            if has_phase2a_section:
                # Table already has section context from Phase 2A — skip
                continue

            # Get page-level heading for this table (unambiguous only)
            heading_group = get_table_page_heading(page_results, page_num, table_idx)
            if heading_group is None:
                continue

            # Apply page-level heading conditions to parameter rows
            for row in et.rows:
                if row.row_type != RowType.PARAMETER:
                    continue

                # Apply page-level heading conditions to page_default layer
                # IMPORTANT: Do NOT skip if resolved_condition is already set.
                # Phase 2B should ALWAYS apply to page_default layer.
                # The unified resolver will handle merging later.
                conditions = heading_group.default_conditions
                if not conditions:
                    continue

                # Initialize condition_context if not present
                if row.condition_context is None:
                    row.condition_context = RowConditionContext()

                # Write to page_default layer
                row.condition_context.page_default.values.update(conditions)
                row.condition_context.page_default.source_row_ids.append(row.row_id)
                row.condition_context.page_default.evidence_type = "page_heading"
                row.condition_context.page_default.source_texts.append(heading_group.full_text)

                # Update legacy fields for backward compatibility
                if not row.default_conditions:
                    row.default_conditions = dict(conditions)
                row.condition_sources = {
                    "row": row.condition_sources.get("row") if row.condition_sources else None,
                    "table_heading": row.condition_sources.get("table_heading") if row.condition_sources else None,
                    "page_heading": heading_group.full_text,
                }
                row.context_status = ContextStatus.RESOLVED
                if "page_heading_applied" not in row.quality_flags:
                    row.quality_flags = list(row.quality_flags) + ["page_heading_applied"]


# ─────────────────────────────────────────────────────────────────────────────
# Final Resolver: Generate resolved_condition from condition layers
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_all_row_conditions(enriched: EnrichedPayload) -> None:
    """
    Final pass: Resolve condition_context for all rows and generate resolved_condition.

    This runs AFTER all enrichment phases (Phase 1, 2A, 2B, 3A, 3B) are complete.
    It calls the unified resolver on each row's condition_context to generate
    the final resolved_condition string.

    Priority for same-key conflicts:
        raw > shared_group > table_default > page_default

    Different keys are ALWAYS preserved.
    """
    for ep in enriched.pages:
        for et in ep.tables:
            for row in et.rows:
                if row.row_type != RowType.PARAMETER:
                    continue

                # Initialize condition_context if not present (backward compatibility)
                if row.condition_context is None:
                    row.condition_context = RowConditionContext()

                # Skip if no conditions at all
                ctx = row.condition_context
                has_any_conditions = (
                    ctx.raw.values or
                    ctx.shared_group.values or
                    ctx.table_default.values or
                    ctx.page_default.values
                )

                if not has_any_conditions:
                    row.resolved_condition = row.raw_condition  # Fall back to raw_condition
                    continue

                # Resolve the condition context
                result = resolve_condition_context(ctx)

                # Apply the resolved condition to the row
                apply_resolved_condition_to_row(row, result)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3A: Shared condition propagation
# ─────────────────────────────────────────────────────────────────────────────

def apply_shared_condition_propagation(enriched: EnrichedPayload) -> None:
    """
    Phase 3A: Propagate shared test conditions to contiguous PARAMETER rows.

    Within the same Camelot table and section, when a group of contiguous
    parameter rows clearly share the same test conditions, propagate the
    conditions to rows that have empty raw_condition.

    Conservative rules:
    - Same table (no cross-table propagation)
    - Same section or both without section_title
    - Contiguous PARAMETER rows
    - Source row has meaningful test conditions (VGS, IF, VR, etc.)
    - Target row has empty raw_condition
    - Max propagation distance <= 2
    - Temperature conditions (TC/TJ) from Phase 2B are preserved

    Note: Without cell-level coordinate evidence, this is INFERRED shared
    condition propagation, NOT confirmed merged cell recovery.
    """
    result = propagate_shared_conditions(enriched)

    # Mark source rows
    apply_propagation_to_source(enriched, result)

    # Update Phase 3A diagnostics in EnrichedPayload
    enriched.shared_condition_groups_detected = result.groups_detected
    enriched.shared_conditions_propagated = result.propagated_count
    enriched.ambiguous_shared_groups = result.ambiguous_groups
    enriched.condition_conflicts = result.conflicts


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
