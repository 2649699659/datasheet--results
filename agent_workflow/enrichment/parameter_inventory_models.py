"""
parameter_inventory_models.py — Data models for Parameter Inventory.

Phase 5: Extract all parameter rows from PDF, not just predefined target fields.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MappingStatus(str, Enum):
    """Whether the parameter is mapped to a canonical field."""
    MAPPED = "mapped"               # Successfully mapped to canonical field
    UNMAPPED = "unmapped"           # Could not map to any canonical field
    NEEDS_REVIEW = "needs_review"   # UNKNOWN row that looks like a parameter
    DUPLICATE = "duplicate"         # Duplicate of another parameter


class ExtractionStatus(str, Enum):
    """How the parameter was extracted."""
    DIRECT = "direct"               # Directly from source (no LLM)
    FROM_CONDITION = "from_condition"  # Derived from condition
    RECONSTRUCTED = "reconstructed"  # Reconstructed from source_cells


# ─────────────────────────────────────────────────────────────────────────────
# Parameter Record
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ParameterRecord:
    """
    A single parameter row extracted from the PDF.

    This is independent from Agent2Result - it represents ALL parameters
    in the PDF, not just the canonical target fields.
    """
    # Identity
    record_id: str                  # Stable ID: "inv_{page}_{table}_{row}"
    file_name: str
    page_number: int
    table_index: int
    row_index: int
    row_id: str                     # Original row_id from EnrichedRow

    # Context
    section_title: str | None = None
    table_title: str | None = None

    # Parameter data (from source cells)
    symbol: str | None = None       # First cell (often the symbol)
    parameter_name: str | None = None  # Full parameter name
    value: str | float | None = None  # For Values tables (numeric or range string)
    min: float | None = None        # Min column
    typ: float | None = None        # Typ column
    max: float | None = None        # Max column
    unit: str | None = None         # Unit string

    # Condition (from Step 0.5 enrichment)
    raw_condition: str | None = None
    resolved_condition: str | None = None

    # Source tracking
    source_schema_type: str | None = None  # "values" or "min_typ_max"
    source_headers: list[str] = field(default_factory=list)  # Table column headers
    source_cells: list[str] = field(default_factory=list)     # Raw cells from PDF
    source_text: str | None = None    # Full text representation
    source_text_reconstructed: bool = False  # True if reconstructed from cells

    # Quality
    extraction_status: ExtractionStatus = ExtractionStatus.DIRECT
    quality_flags: list[str] = field(default_factory=list)

    # Canonical mapping (filled after Agent2 runs)
    canonical_field_id: str | None = None
    mapping_status: MappingStatus = MappingStatus.UNMAPPED
    source_row_id: str | None = None  # Agent2's source_row_id for mapping

    # Duplicate tracking
    duplicate_group_id: str | None = None

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "file_name": self.file_name,
            "page_number": self.page_number,
            "table_index": self.table_index,
            "row_index": self.row_index,
            "row_id": self.row_id,
            "section_title": self.section_title,
            "table_title": self.table_title,
            "symbol": self.symbol,
            "parameter_name": self.parameter_name,
            "value": self.value,
            "min": self.min,
            "typ": self.typ,
            "max": self.max,
            "unit": self.unit,
            "raw_condition": self.raw_condition,
            "resolved_condition": self.resolved_condition,
            "source_schema_type": self.source_schema_type,
            "source_headers": self.source_headers,
            "source_cells": self.source_cells,
            "source_text": self.source_text,
            "source_text_reconstructed": self.source_text_reconstructed,
            "extraction_status": self.extraction_status.value if isinstance(self.extraction_status, ExtractionStatus) else self.extraction_status,
            "quality_flags": self.quality_flags,
            "canonical_field_id": self.canonical_field_id,
            "mapping_status": self.mapping_status.value if isinstance(self.mapping_status, MappingStatus) else self.mapping_status,
            "source_row_id": self.source_row_id,
            "duplicate_group_id": self.duplicate_group_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ParameterRecord":
        return cls(
            record_id=d["record_id"],
            file_name=d["file_name"],
            page_number=d["page_number"],
            table_index=d["table_index"],
            row_index=d["row_index"],
            row_id=d["row_id"],
            section_title=d.get("section_title"),
            table_title=d.get("table_title"),
            symbol=d.get("symbol"),
            parameter_name=d.get("parameter_name"),
            value=d.get("value"),
            min=d.get("min"),
            typ=d.get("typ"),
            max=d.get("max"),
            unit=d.get("unit"),
            raw_condition=d.get("raw_condition"),
            resolved_condition=d.get("resolved_condition"),
            source_schema_type=d.get("source_schema_type"),
            source_headers=list(d.get("source_headers", [])),
            source_cells=list(d.get("source_cells", [])),
            source_text=d.get("source_text"),
            source_text_reconstructed=d.get("source_text_reconstructed", False),
            extraction_status=ExtractionStatus(d["extraction_status"]) if d.get("extraction_status") in [e.value for e in ExtractionStatus] else ExtractionStatus.DIRECT,
            quality_flags=list(d.get("quality_flags", [])),
            canonical_field_id=d.get("canonical_field_id"),
            mapping_status=MappingStatus(d["mapping_status"]) if d.get("mapping_status") in [e.value for e in MappingStatus] else MappingStatus.UNMAPPED,
            source_row_id=d.get("source_row_id"),
            duplicate_group_id=d.get("duplicate_group_id"),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Inventory Report
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class InventoryReport:
    """Summary report of the parameter inventory generation."""
    total_rows_processed: int = 0
    parameter_rows_found: int = 0
    unknown_rows_found: int = 0
    unknown_parameter_like: int = 0

    # Classification breakdown
    mapped_count: int = 0
    unmapped_count: int = 0
    needs_review_count: int = 0
    duplicate_count: int = 0

    # Quality issues
    missing_value_slots: int = 0
    missing_source_text: int = 0
    reconstructed_source_text: int = 0

    # Schema breakdown
    values_table_count: int = 0
    min_typ_max_table_count: int = 0

    # Page/table coverage
    pages_covered: int = 0
    tables_covered: int = 0

    def to_dict(self) -> dict:
        return {
            "total_rows_processed": self.total_rows_processed,
            "parameter_rows_found": self.parameter_rows_found,
            "unknown_rows_found": self.unknown_rows_found,
            "unknown_parameter_like": self.unknown_parameter_like,
            "mapped_count": self.mapped_count,
            "unmapped_count": self.unmapped_count,
            "needs_review_count": self.needs_review_count,
            "duplicate_count": self.duplicate_count,
            "missing_value_slots": self.missing_value_slots,
            "missing_source_text": self.missing_source_text,
            "reconstructed_source_text": self.reconstructed_source_text,
            "values_table_count": self.values_table_count,
            "min_typ_max_table_count": self.min_typ_max_table_count,
            "pages_covered": self.pages_covered,
            "tables_covered": self.tables_covered,
        }
