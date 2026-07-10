"""
Data Models for Extracted Parameters

Defines the standard data structures used throughout the pipeline.

Classes:
    RawExtractedParam: Unified parameter extracted from PDF
    FieldConfig: Configuration for a target field from YAML

Enums:
    ParamStatus: Status of extracted parameter
    ExtractionMethod: How the parameter was extracted
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List


class ParamStatus(str, Enum):
    """Status of an extracted parameter."""
    CONFIRMED = "confirmed"      # Value is confirmed, has source
    NEEDS_REVIEW = "needs_review"  # Needs human review
    REJECTED = "rejected"        # Rejected or invalid


class ExtractionMethod(str, Enum):
    """Method used to extract the parameter."""
    RULE_TABLE = "rule_table"    # Extracted from table using rules
    RULE_TEXT = "rule_text"      # Extracted from text using rules
    LLM = "llm"                 # Extracted using LLM
    MANUAL = "manual"           # Manually entered


class UnitConversionStatus(str, Enum):
    """Status of unit conversion."""
    NOT_NEEDED = "not_needed"    # No conversion needed
    SUCCESS = "success"          # Conversion successful
    FAILED = "failed"           # Conversion failed
    NOT_SUPPORTED = "not_supported"  # Units not convertible


@dataclass
class RawExtractedParam:
    """
    Unified Raw Extracted Parameter data structure.
    
    All fields are optional - not every extraction will populate all fields.
    """
    # ========== Source Identity ==========
    # PDF/Document identification
    pdf_path: str = ""
    file_name: str = ""
    document_id: str = ""        # Unique ID for multi-PDF isolation
    pdf_stem: str = ""          # Filename without extension
    
    # Part identification
    part_number: str = ""
    manufacturer: str = ""
    
    # ========== Field Identification ==========
    field_id: str = ""           # ID from target_fields.yaml
    label: str = ""              # Human-readable label
    category: str = ""           # Field category (from config)
    priority: str = "medium"     # Field priority (low/medium/high)
    
    # ========== Parameter Value ==========
    symbol: str = ""             # Parameter symbol (e.g., "RDS(on)")
    parameter: str = ""           # Full parameter name
    applies_to: List[str] = field(default_factory=lambda: ["module", "discrete_mosfet", "die", "unknown"])
    
    # Value fields (min/typ/max)
    min: Optional[float] = None
    typ: Optional[float] = None
    max: Optional[float] = None
    
    # Raw value (when single value, not min/typ/max)
    value: Optional[float] = None
    
    # ========== Units ==========
    unit: str = ""               # Final/normalized unit
    original_unit: str = ""      # Unit as it appeared in PDF
    normalized_unit: str = ""     # Unit after normalization
    
    # ========== Source Evidence ==========
    source_page: int = 0
    table_index: int = -1       # Which table on the page
    row_index: int = -1         # Which row in the table
    source_text: str = ""        # Raw text from PDF
    source_hash: str = ""        # Hash of source for dedup
    
    # ========== Row Structure (Step 5) ==========
    row_cells: List[str] = field(default_factory=list)  # Actual row cells/columns
    row_cell_count: int = 0     # Number of cells in the row
    nearby_header_rows: List[List[str]] = field(default_factory=list)  # Header rows for column inference
    previous_row_text: str = ""  # Previous row text (for context)
    next_row_text: str = ""      # Next row text (for context)
    condition: str = ""          # Extracted condition string
    condition_values: List[str] = field(default_factory=list)  # List of condition key-values (Step 5.5)
    
    # ========== Quality Tracking ==========
    confidence: float = 0.0     # 0.0 to 1.0
    status: ParamStatus = ParamStatus.NEEDS_REVIEW
    method: ExtractionMethod = ExtractionMethod.RULE_TABLE
    
    # ========== Matching Strategy Fields (Step 4.7) ==========
    match_type: str = ""         # "exact", "symbol", "fuzzy"
    match_policy: str = "normal"  # "normal", "strict_rating", "metadata_text"
    accept_reason: str = ""      # Why the candidate was accepted
    reject_reason: str = ""       # Why the candidate was rejected (if rejected)
    candidate_status: str = "active"  # "active", "rejected", "weak"
    
    # ========== Unit Conversion ==========
    original_value: Optional[float] = None  # Value before conversion
    normalized_value: Optional[float] = None  # Value after normalization (Step 5: always None)
    unit_conversion_status: UnitConversionStatus = UnitConversionStatus.NOT_NEEDED
    unit_conversion_note: str = ""          # Error message if conversion failed
    
    # ========== Review Information ==========
    review_reason: str = ""      # Why it needs review
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            # Source Identity
            "pdf_path": self.pdf_path,
            "file_name": self.file_name,
            "document_id": self.document_id,
            "pdf_stem": self.pdf_stem,
            "part_number": self.part_number,
            "manufacturer": self.manufacturer,
            # Field Identification
            "field_id": self.field_id,
            "label": self.label,
            "category": self.category,
            "priority": self.priority,
            # Parameter Value
            "symbol": self.symbol,
            "parameter": self.parameter,
            "applies_to": self.applies_to,
            "min": self.min,
            "typ": self.typ,
            "max": self.max,
            "value": self.value,
            # Units
            "unit": self.unit,
            "original_unit": self.original_unit,
            "normalized_unit": self.normalized_unit,
            # Parameter Value (Step 5)
            "normalized_value": self.normalized_value,
            # Source Evidence
            "source_page": self.source_page,
            "table_index": self.table_index,
            "row_index": self.row_index,
            "source_text": self.source_text,
            "source_hash": self.source_hash,
            # Row Structure (Step 5)
            "row_cells": self.row_cells,
            "row_cell_count": self.row_cell_count,
            "nearby_header_rows": self.nearby_header_rows,
            "previous_row_text": self.previous_row_text,
            "next_row_text": self.next_row_text,
            "condition": self.condition,
            "condition_values": self.condition_values,
            # Quality Tracking
            "confidence": self.confidence,
            "status": self.status.value if isinstance(self.status, Enum) else self.status,
            "method": self.method.value if isinstance(self.method, Enum) else self.method,
            # Unit Conversion
            "original_value": self.original_value,
            "unit_conversion_status": self.unit_conversion_status.value if isinstance(self.unit_conversion_status, Enum) else self.unit_conversion_status,
            "unit_conversion_note": self.unit_conversion_note,
            # Review Information
            "review_reason": self.review_reason,
            # Matching Strategy Fields (Step 4.7)
            "match_type": self.match_type,
            "match_policy": self.match_policy,
            "accept_reason": self.accept_reason,
            "reject_reason": self.reject_reason,
            "candidate_status": self.candidate_status,
            # Alias (for compatibility)
            "matched_alias": self.symbol,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "RawExtractedParam":
        """Create from dictionary."""
        # Handle enum conversions
        status = data.get("status", "needs_review")
        if isinstance(status, str):
            status = ParamStatus(status)
        
        method = data.get("method", "rule_table")
        if isinstance(method, str):
            method = ExtractionMethod(method)
        
        unit_conv_status = data.get("unit_conversion_status", "not_needed")
        if isinstance(unit_conv_status, str):
            unit_conv_status = UnitConversionStatus(unit_conv_status)
        
        return cls(
            # Source Identity
            pdf_path=data.get("pdf_path", ""),
            file_name=data.get("file_name", ""),
            document_id=data.get("document_id", ""),
            pdf_stem=data.get("pdf_stem", ""),
            part_number=data.get("part_number", ""),
            manufacturer=data.get("manufacturer", ""),
            # Field Identification
            field_id=data.get("field_id", ""),
            label=data.get("label", ""),
            category=data.get("category", ""),
            priority=data.get("priority", "medium"),
            # Parameter Value
            symbol=data.get("symbol", ""),
            parameter=data.get("parameter", ""),
            applies_to=data.get("applies_to", ["module", "discrete_mosfet", "die", "unknown"]),
            min=data.get("min"),
            typ=data.get("typ"),
            max=data.get("max"),
            value=data.get("value"),
            # Units
            unit=data.get("unit", ""),
            original_unit=data.get("original_unit", ""),
            normalized_unit=data.get("normalized_unit", ""),
            # Source Evidence
            source_page=data.get("source_page", 0),
            table_index=data.get("table_index", -1),
            row_index=data.get("row_index", -1),
            source_text=data.get("source_text", ""),
            source_hash=data.get("source_hash", ""),
            # Row Structure (Step 5)
            row_cells=data.get("row_cells", []),
            row_cell_count=data.get("row_cell_count", 0),
            nearby_header_rows=data.get("nearby_header_rows", []),
            previous_row_text=data.get("previous_row_text", ""),
            next_row_text=data.get("next_row_text", ""),
            condition=data.get("condition", ""),
            condition_values=data.get("condition_values", []),
            # Quality Tracking
            confidence=data.get("confidence", 0.0),
            status=status,
            method=method,
            # Unit Conversion
            original_value=data.get("original_value"),
            normalized_value=data.get("normalized_value"),
            unit_conversion_status=unit_conv_status,
            unit_conversion_note=data.get("unit_conversion_note", ""),
            # Review Information
            review_reason=data.get("review_reason", ""),
            # Matching Strategy Fields (Step 4.7)
            match_type=data.get("match_type", ""),
            match_policy=data.get("match_policy", "normal"),
            accept_reason=data.get("accept_reason", ""),
            reject_reason=data.get("reject_reason", ""),
            candidate_status=data.get("candidate_status", "active"),
        )


@dataclass
class FieldConfig:
    """
    Configuration for a target field from YAML.
    """
    id: str
    label: str
    unit: str
    aliases: List[str]
    preferred_value: str  # "min", "typ", or "max"
    condition_keywords: List[str] = field(default_factory=list)
    notes: str = ""
    
    # Extended fields with defaults
    category: str = "uncategorized"
    applies_to: List[str] = field(default_factory=lambda: ["module", "discrete_mosfet", "die", "unknown"])
    priority: str = "medium"
    unit_conversion: bool = True
    
    # Matching Policy Fields (Step 4.7)
    expected_sources: List[str] = field(default_factory=lambda: ["table"])
    match_strategy: str = "normal"  # "normal", "strict_rating", "metadata_text"
    allow_fuzzy: bool = True
    required_context: List[str] = field(default_factory=list)
    forbidden_context: List[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: dict) -> "FieldConfig":
        """Create from dictionary with defaults for extended fields."""
        return cls(
            id=data["id"],
            label=data["label"],
            unit=data.get("unit", ""),
            aliases=data.get("aliases", []),
            preferred_value=data.get("preferred_value", "typ"),
            condition_keywords=data.get("condition_keywords", []),
            notes=data.get("notes", ""),
            category=data.get("category", "uncategorized"),
            applies_to=data.get("applies_to", ["module", "discrete_mosfet", "die", "unknown"]),
            priority=data.get("priority", "medium"),
            unit_conversion=data.get("unit_conversion", True),
            # Matching Policy Fields (Step 4.7)
            expected_sources=data.get("expected_sources", ["table"]),
            match_strategy=data.get("match_strategy", "normal"),
            allow_fuzzy=data.get("allow_fuzzy", True),
            required_context=data.get("required_context", []),
            forbidden_context=data.get("forbidden_context", []),
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "label": self.label,
            "unit": self.unit,
            "aliases": self.aliases,
            "preferred_value": self.preferred_value,
            "condition_keywords": self.condition_keywords,
            "notes": self.notes,
            "category": self.category,
            "applies_to": self.applies_to,
            "priority": self.priority,
            "unit_conversion": self.unit_conversion,
            # Matching Policy Fields (Step 4.7)
            "expected_sources": self.expected_sources,
            "match_strategy": self.match_strategy,
            "allow_fuzzy": self.allow_fuzzy,
            "required_context": self.required_context,
            "forbidden_context": self.forbidden_context,
        }
