"""
contracts.py — Unified data structures for the Agent Workflow

These dataclasses define the contract between each step.
Each step reads an input contract and produces an output contract.
"""

from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class FieldStatus(str, Enum):
    """Parameter selection status."""
    FINAL = "final"
    REVIEW_NEEDED = "review_needed"
    BLOCKED = "blocked"
    MISSING = "missing"


# ─────────────────────────────────────────────────────────────────────────────
# Step 0: Camelot Payload
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CamelotTableRow:
    """A single row in a Camelot table."""
    row_index: int
    cells: list[str]


@dataclass
class CamelotTable:
    """A single extracted table."""
    page_number: int
    table_index: int
    flavor: str  # "lattice" or "stream"
    rows: list[CamelotTableRow]
    accuracy: float | None
    whitespace: float | None
    score: float = 0.0  # quality score


@dataclass
class CamelotPage:
    """A single page."""
    page_number: int
    tables: list[CamelotTable]


@dataclass
class CamelotPayload:
    """
    Output of Step 0: Camelot table extraction.

    This wraps the raw ExtractedDocument into a clean, JSON-serializable format.
    """
    document_id: str
    file_name: str
    pdf_path: str
    pages: list[CamelotPage]
    source_backend: str = "camelot"

    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "file_name": self.file_name,
            "pdf_path": self.pdf_path,
            "pages": [
                {
                    "page_number": p.page_number,
                    "tables": [
                        {
                            "page_number": t.page_number,
                            "table_index": t.table_index,
                            "flavor": t.flavor,
                            "rows": [
                                {"row_index": r.row_index, "cells": r.cells}
                                for r in t.rows
                            ],
                            "accuracy": t.accuracy,
                            "whitespace": t.whitespace,
                            "score": t.score,
                        }
                        for t in p.tables
                    ]
                }
                for p in self.pages
            ],
            "source_backend": self.source_backend,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CamelotPayload":
        pages = []
        for p in d["pages"]:
            tables = []
            for t in p["tables"]:
                rows = [
                    CamelotTableRow(row_index=r["row_index"], cells=r["cells"])
                    for r in t["rows"]
                ]
                tables.append(CamelotTable(
                    page_number=t["page_number"],
                    table_index=t["table_index"],
                    flavor=t["flavor"],
                    rows=rows,
                    accuracy=t.get("accuracy"),
                    whitespace=t.get("whitespace"),
                    score=t.get("score", 0.0),
                ))
            pages.append(CamelotPage(page_number=p["page_number"], tables=tables))
        return cls(
            document_id=d["document_id"],
            file_name=d["file_name"],
            pdf_path=d["pdf_path"],
            pages=pages,
            source_backend=d.get("source_backend", "camelot"),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Agent 1 — Candidate Rows
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CandidateParam:
    """A single parameter value parsed from a candidate row."""
    value: float | None = None
    min: float | None = None
    typ: float | None = None
    max: float | None = None
    unit: str | None = None
    original_unit: str | None = None


@dataclass
class CandidateRow:
    """
    A single candidate row for a field.

    Produced by Step 1 (Agent 1) and consumed by Step 2 (Agent 2).
    """
    field_id: str
    label: str
    symbol: str | None
    parameter_name: str | None
    # Raw candidate data
    candidate_type: str  # "selected" | "review" | "rejected"
    source_page: int
    table_index: int
    row_index: int
    row_cells: list[str]  # full row text for context
    source_text: str  # reconstructed source text
    # Parsed values
    value: float | None = None
    min: float | None = None
    typ: float | None = None
    max: float | None = None
    unit: str | None = None
    original_unit: str | None = None
    condition: str | None = None
    # Confidence
    confidence: float = 0.0
    match_type: str = "unknown"  # "exact" | "symbol" | "fuzzy" | "text_match"
    warnings: list[str] = field(default_factory=list)
    review_reason: str | None = None


@dataclass
class FieldCandidates:
    """All candidates for a single field."""
    field_id: str
    label: str
    target_unit: str
    candidates: list[CandidateRow]
    selected_candidate: CandidateRow | None = None


@dataclass
class Agent1Result:
    """
    Output of Step 1 (Agent 1): Candidate row selection and classification.

    The LLM reviews Camelot tables and selects best candidate rows per field.
    """
    document_id: str
    file_name: str
    fields: list[FieldCandidates]
    total_candidates: int
    selected_count: int
    review_count: int

    def to_dict(self) -> dict:
        def candidate_to_dict(c: CandidateRow) -> dict:
            return {
                "field_id": c.field_id,
                "label": c.label,
                "symbol": c.symbol,
                "parameter_name": c.parameter_name,
                "candidate_type": c.candidate_type,
                "source_page": c.source_page,
                "table_index": c.table_index,
                "row_index": c.row_index,
                "source_text": c.source_text,
                "row_cells": c.row_cells,
                "value": c.value,
                "min": c.min,
                "typ": c.typ,
                "max": c.max,
                "unit": c.unit,
                "original_unit": c.original_unit,
                "condition": c.condition,
                "confidence": c.confidence,
                "match_type": c.match_type,
                "warnings": c.warnings,
                "review_reason": c.review_reason,
            }

        return {
            "document_id": self.document_id,
            "file_name": self.file_name,
            "fields": [
                {
                    "field_id": f.field_id,
                    "label": f.label,
                    "target_unit": f.target_unit,
                    "candidates": [candidate_to_dict(c) for c in f.candidates],
                    "selected_candidate": candidate_to_dict(f.selected_candidate) if f.selected_candidate else None,
                }
                for f in self.fields
            ],
            "total_candidates": self.total_candidates,
            "selected_count": self.selected_count,
            "review_count": self.review_count,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Agent 2 — Validated Final Params
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Agent2Param:
    """
    A validated parameter from Step 2 (Agent 2).

    Replaces the legacy PipelineCandidate / PipelineParam.
    """
    field_id: str
    status: FieldStatus
    # Values
    value: float | None
    min: float | None
    typ: float | None
    max: float | None
    unit: str | None
    condition: str | None
    # Source location
    source_page: int | None
    table_index: int | None
    row_index: int | None
    source_text: str | None
    # Quality
    confidence: float
    reason: str
    warnings: list[str] = field(default_factory=list)


@dataclass
class Agent2Result:
    """
    Output of Step 2 (Agent 2): Parameter validation and disambiguation.

    The LLM reviews Agent 1 candidates and:
    - Confirms correct selections
    - Corrects wrong selections
    - Blocks invalid candidates
    - Flags ambiguous cases for review
    """
    document_id: str
    file_name: str
    overall_status: str  # "pass" | "needs_review" | "unsafe"
    final_params: list[Agent2Param]
    summary: dict  # final_count, review_needed_count, missing_count, blocked_count

    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "file_name": self.file_name,
            "overall_status": self.overall_status,
            "final_params": [
                {
                    "field_id": p.field_id,
                    "status": p.status.value if isinstance(p.status, FieldStatus) else p.status,
                    "value": p.value,
                    "min": p.min,
                    "typ": p.typ,
                    "max": p.max,
                    "unit": p.unit,
                    "condition": p.condition,
                    "source_page": p.source_page,
                    "table_index": p.table_index,
                    "row_index": p.row_index,
                    "source_text": p.source_text,
                    "confidence": p.confidence,
                    "reason": p.reason,
                    "warnings": p.warnings,
                }
                for p in self.final_params
            ],
            "summary": self.summary,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Agent 3 — Consistency Report
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ConsistencyCheck:
    """Result of a single consistency rule check."""
    rule_id: str
    rule_name: str
    severity: str  # "critical" | "high" | "medium"
    status: str  # "pass" | "fail" | "skipped" | "warning"
    fields_involved: list[str]
    details: dict
    verdict: str
    suggested_action: str  # "none" | "review" | "warning" | "block"


@dataclass
class Agent3Result:
    """
    Output of Step 3 (Agent 3): Cross-parameter consistency check.

    Validates relationships between parameters (e.g., QG > QGS + QGD,
    RDS(on)@150°C > RDS(on)@25°C, Ciss > Coss > Crss, etc.)
    """
    document_id: str
    file_name: str
    overall_status: str  # "consistent" | "inconsistent" | "review_needed"
    consistency_checks: list[ConsistencyCheck]
    summary: dict  # total_checks, passed, failed, skipped, warnings
    recommendations: list[str]

    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "file_name": self.file_name,
            "overall_status": self.overall_status,
            "consistency_checks": [
                {
                    "rule_id": c.rule_id,
                    "rule_name": c.rule_name,
                    "severity": c.severity,
                    "status": c.status,
                    "fields_involved": c.fields_involved,
                    "details": c.details,
                    "verdict": c.verdict,
                    "suggested_action": c.suggested_action,
                }
                for c in self.consistency_checks
            ],
            "summary": self.summary,
            "recommendations": self.recommendations,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Excel Input
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ExcelInput:
    """
    Input for Step 4: Excel generation.

    Combines validated params (Agent 2) with consistency report (Agent 3).
    """
    agent2: Agent2Result
    agent3: Agent3Result
    pdf_path: str
    output_xlsx_path: str | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Workflow Result
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class WorkflowResult:
    """
    Final result of the entire Agent Workflow.
    """
    pdf_path: str
    output_xlsx: str
    status: str  # "success" | "partial" | "failed"
    agent1: Agent1Result | None
    agent2: Agent2Result | None
    agent3: Agent3Result | None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0
