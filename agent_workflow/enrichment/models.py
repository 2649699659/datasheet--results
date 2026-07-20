"""
models.py — Data models for the enrichment layer.

These dataclasses are independent from the CamelotPayload contracts.
They provide enriched context for each extracted row without modifying
the original CamelotPayload structure.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RowType(str, Enum):
    """Row classification types (conservative, Phase 1)."""
    PARAMETER = "parameter"           # Likely a data row with values
    TABLE_TITLE = "table_title"       # Table-level title/header
    SECTION_TITLE = "section_title"   # Section-level header (e.g., "Static characteristics")
    COLUMN_HEADER = "column_header"    # Column headers (Symbol, Unit, Min, etc.)
    SEPARATOR = "separator"           # Row of dashes, lines, or whitespace-only
    EMPTY = "empty"                   # All cells empty
    UNKNOWN = "unknown"               # Cannot be reliably classified


class ContextStatus(str, Enum):
    """How a row's context was resolved."""
    UNCHANGED = "unchanged"   # No context resolution needed
    RESOLVED = "resolved"     # Context resolved from nearby rows
    AMBIGUOUS = "ambiguous"    # Context is ambiguous


# ─────────────────────────────────────────────────────────────────────────────
# Enriched Row
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EnrichedRow:
    """
    An enriched row with classification and context.

    Phase 1 fields (all other fields are None or empty for now):
    """
    # Identity
    row_id: str                        # Stable ID: "p{page}_t{table}_r{row}"
    page_number: int
    table_index: int
    row_index: int

    # Original data (deep-copy from CamelotPayload)
    raw_cells: list[str]

    # Classification
    row_type: RowType

    # Context placeholders (filled in later phases)
    table_title: str | None = None
    section_title: str | None = None

    # Condition placeholders (filled in later phases)
    raw_condition: str | None = None
    resolved_condition: str | None = None
    default_conditions: dict[str, str] = field(default_factory=dict)

    # Phase 2A: Condition sources (where the condition came from)
    # Structure: {"row": str | None, "table_heading": str | None}
    condition_sources: dict[str, str | None] | None = None

    # Status & quality
    context_status: ContextStatus = ContextStatus.UNCHANGED
    quality_flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "row_id": self.row_id,
            "page_number": self.page_number,
            "table_index": self.table_index,
            "row_index": self.row_index,
            "raw_cells": self.raw_cells,
            "row_type": self.row_type.value if isinstance(self.row_type, RowType) else self.row_type,
            "table_title": self.table_title,
            "section_title": self.section_title,
            "raw_condition": self.raw_condition,
            "resolved_condition": self.resolved_condition,
            "default_conditions": self.default_conditions,
            "condition_sources": self.condition_sources,
            "context_status": self.context_status.value if isinstance(self.context_status, ContextStatus) else self.context_status,
            "quality_flags": self.quality_flags,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EnrichedRow":
        return cls(
            row_id=d["row_id"],
            page_number=d["page_number"],
            table_index=d["table_index"],
            row_index=d["row_index"],
            raw_cells=list(d["raw_cells"]),
            row_type=RowType(d["row_type"]) if d["row_type"] in [e.value for e in RowType] else d["row_type"],
            table_title=d.get("table_title"),
            section_title=d.get("section_title"),
            raw_condition=d.get("raw_condition"),
            resolved_condition=d.get("resolved_condition"),
            default_conditions=dict(d.get("default_conditions", {})),
            condition_sources=d.get("condition_sources"),
            context_status=ContextStatus(d["context_status"]) if d["context_status"] in [e.value for e in ContextStatus] else d.get("context_status", "unchanged"),
            quality_flags=list(d.get("quality_flags", [])),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Enriched Table
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EnrichedTable:
    """
    An enriched table preserving CamelotTable metadata.
    """
    page_number: int
    table_index: int
    flavor: str                     # "lattice" or "stream"
    rows: list[EnrichedRow]
    accuracy: float | None
    whitespace: float | None
    score: float = 0.0

    # Phase 1: table_title is the first non-empty, non-header, non-separator row
    table_title: str | None = None

    def to_dict(self) -> dict:
        return {
            "page_number": self.page_number,
            "table_index": self.table_index,
            "flavor": self.flavor,
            "rows": [r.to_dict() for r in self.rows],
            "accuracy": self.accuracy,
            "whitespace": self.whitespace,
            "score": self.score,
            "table_title": self.table_title,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EnrichedTable":
        return cls(
            page_number=d["page_number"],
            table_index=d["table_index"],
            flavor=d["flavor"],
            rows=[EnrichedRow.from_dict(r) for r in d["rows"]],
            accuracy=d.get("accuracy"),
            whitespace=d.get("whitespace"),
            score=d.get("score", 0.0),
            table_title=d.get("table_title"),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Enriched Page
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EnrichedPage:
    """
    An enriched page.
    """
    page_number: int
    tables: list[EnrichedTable]

    def to_dict(self) -> dict:
        return {
            "page_number": self.page_number,
            "tables": [t.to_dict() for t in self.tables],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EnrichedPage":
        return cls(
            page_number=d["page_number"],
            tables=[EnrichedTable.from_dict(t) for t in d["tables"]],
        )


# ─────────────────────────────────────────────────────────────────────────────
# Enriched Payload
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EnrichedPayload:
    """
    Enriched version of CamelotPayload.

    Produced by Step 0.5: enrich_context.
    This is an ADDITIVE enrichment — it does NOT modify the original
    CamelotPayload. Both can coexist.
    """
    document_id: str
    file_name: str
    pdf_path: str
    source_backend: str
    pages: list[EnrichedPage]

    # Metadata about the enrichment
    enriched_row_count: int = 0
    row_type_counts: dict[str, int] = field(default_factory=dict)

    # Phase 2A: Heading detection diagnostics
    table_titles_detected: list[str] = field(default_factory=list)
    section_titles_detected: list[str] = field(default_factory=list)
    heading_conditions_parsed: int = 0       # total heading conditions found
    heading_conditions_applied: int = 0       # conditions applied to parameter rows
    heading_condition_overrides: int = 0      # row-level condition overrode heading
    ambiguous_title_rows: list[str] = field(default_factory=list)  # row_ids that couldn't be titled

    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "file_name": self.file_name,
            "pdf_path": self.pdf_path,
            "source_backend": self.source_backend,
            "pages": [p.to_dict() for p in self.pages],
            "enriched_row_count": self.enriched_row_count,
            "row_type_counts": self.row_type_counts,
            "table_titles_detected": self.table_titles_detected,
            "section_titles_detected": self.section_titles_detected,
            "heading_conditions_parsed": self.heading_conditions_parsed,
            "heading_conditions_applied": self.heading_conditions_applied,
            "heading_condition_overrides": self.heading_condition_overrides,
            "ambiguous_title_rows": self.ambiguous_title_rows,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EnrichedPayload":
        return cls(
            document_id=d["document_id"],
            file_name=d["file_name"],
            pdf_path=d["pdf_path"],
            source_backend=d.get("source_backend", "camelot"),
            pages=[EnrichedPage.from_dict(p) for p in d["pages"]],
            enriched_row_count=d.get("enriched_row_count", 0),
            row_type_counts=dict(d.get("row_type_counts", {})),
            table_titles_detected=list(d.get("table_titles_detected", [])),
            section_titles_detected=list(d.get("section_titles_detected", [])),
            heading_conditions_parsed=d.get("heading_conditions_parsed", 0),
            heading_conditions_applied=d.get("heading_conditions_applied", 0),
            heading_condition_overrides=d.get("heading_condition_overrides", 0),
            ambiguous_title_rows=list(d.get("ambiguous_title_rows", [])),
        )

    def _recompute_stats(self) -> None:
        """
        Recompute row counts, type distribution, and Phase 2A diagnostics.
        """
        self.enriched_row_count = 0
        self.row_type_counts = {}
        self.table_titles_detected = []
        self.section_titles_detected = []
        self.heading_conditions_parsed = 0
        self.heading_conditions_applied = 0
        self.heading_condition_overrides = 0
        self.ambiguous_title_rows = []

        for page in self.pages:
            for table in page.tables:
                for row in table.rows:
                    self.enriched_row_count += 1
                    rt = row.row_type.value if isinstance(row.row_type, RowType) else row.row_type
                    self.row_type_counts[rt] = self.row_type_counts.get(rt, 0) + 1

                    # Phase 2A diagnostics
                    if row.table_title:
                        self.table_titles_detected.append(row.table_title)
                    if row.section_title:
                        self.section_titles_detected.append(row.section_title)
                    if row.default_conditions:
                        self.heading_conditions_parsed += len(row.default_conditions)
                    if row.condition_sources:
                        src = row.condition_sources.get("table_heading")
                        if src:
                            self.heading_conditions_applied += 1
                        if row.condition_sources.get("row"):
                            self.heading_condition_overrides += 1
                    if row.context_status == ContextStatus.AMBIGUOUS:
                        self.ambiguous_title_rows.append(row.row_id)
