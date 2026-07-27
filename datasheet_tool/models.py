"""
models.py — Simplified data structures for datasheet_tool

A minimal set of dataclasses for the 4-step extraction flow:
PDF → Camelot → AI Agent → Review → Excel
"""

from dataclasses import dataclass, field, asdict
from typing import Any
import json


# ─────────────────────────────────────────────────────────────────────────────
# Raw Table (from Camelot)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RawTable:
    """A single raw table extracted by Camelot."""
    page: int
    table_index: int
    flavor: str  # "lattice" or "stream"
    rows: list[list[str]]  # [[cell, cell, ...], ...]
    accuracy: float | None = None
    score: float = 0.0


@dataclass
class RawDocument:
    """Complete raw document from Camelot extraction."""
    pdf_path: str
    file_name: str
    tables: list[RawTable]


# ─────────────────────────────────────────────────────────────────────────────
# Extracted Parameter (from AI Agent)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Parameter:
    """
    A single extracted parameter from a datasheet table.
    
    Simplified structure - no enrichment, no canonical mapping, no complex status.
    """
    symbol: str | None = None       # e.g., "RDS(on)", "VGS(th)"
    name: str | None = None        # e.g., "Drain-Source On Resistance"
    value: str | float | None = None  # For single-value tables
    min: str | float | None = None
    typ: str | float | None = None
    max: str | float | None = None
    unit: str | None = None        # e.g., "mΩ", "V", "nC"
    condition: str | None = None   # e.g., "VGS=18V; ID=300A"
    page: int = 0                  # Source page number
    table_index: int = 0          # Source table index on page
    row_index: int = 0            # Source row index in table
    source_text: str | None = None  # Original row text for reference
    confidence: float = 1.0       # 0.0 - 1.0, AI confidence score
    needs_review: bool = False     # True if needs human review
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, d: dict) -> "Parameter":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
    
    def should_review(self) -> bool:
        """Check if this parameter needs review based on simple rules."""
        if self.needs_review:
            return True
        if self.confidence < 0.8:
            return True
        # Missing unit but has value
        if not self.unit and (self.value or self.min or self.typ or self.max):
            return True
        # Has unit but no actual value
        if self.unit and not (self.value or self.min or self.typ or self.max):
            return True
        # No value at all
        if not (self.value or self.min or self.typ or self.max):
            return True
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Document Metadata
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DocumentInfo:
    """Document-level metadata."""
    manufacturer: str | None = None
    part_number: str | None = None
    module_type: str | None = None
    description: str | None = None
    file_name: str = ""
    pdf_path: str = ""
    processing_time_seconds: float = 0.0
    total_parameters: int = 0
    needs_review_count: int = 0
    
    def to_dict(self) -> dict:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# Extraction Result
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ExtractionResult:
    """Complete extraction result."""
    document_info: DocumentInfo
    parameters: list[Parameter]
    
    def to_dict(self) -> dict:
        return {
            "metadata": self.document_info.to_dict(),
            "parameters": [p.to_dict() for p in self.parameters],
        }
    
    def save_json(self, path: str):
        """Save result to JSON file."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load_json(cls, path: str) -> "ExtractionResult":
        """Load result from JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        doc_info = DocumentInfo(**d["metadata"])
        params = [Parameter.from_dict(p) for p in d["parameters"]]
        return cls(document_info=doc_info, parameters=params)
