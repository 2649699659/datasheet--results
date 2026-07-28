"""
enrichment — Context enrichment layer for CamelotPayload.

Provides row-level classification and context enrichment without modifying
the original CamelotPayload structure.

Phase 1: Row-level classification.
Phase 2A: Table/section title tracking and temperature condition resolution.
"""

from .models import (
    EnrichedPayload,
    EnrichedTable,
    EnrichedPage,
    EnrichedRow,
    RowType,
    ContextStatus,
)
from .row_classifier import RowClassifier
from .enricher import enrich_payload
from .heading_parser import (
    parse_temperature_from_text,
    extract_temperature_from_cells,
    extract_raw_condition_from_cells,
    extract_condition_from_heading,
    has_temperature_condition,
)
from .parameter_inventory_models import (
    ParameterRecord,
    InventoryReport,
    MappingStatus,
    ExtractionStatus,
)
from .materialize_parameter_inventory import (
    materialize_parameter_inventory,
)

__all__ = [
    # Models
    "EnrichedPayload",
    "EnrichedTable",
    "EnrichedPage",
    "EnrichedRow",
    "RowType",
    "ContextStatus",
    # Classifier
    "RowClassifier",
    # Enricher
    "enrich_payload",
    # Heading parser
    "parse_temperature_from_text",
    "extract_temperature_from_cells",
    "extract_raw_condition_from_cells",
    "extract_condition_from_heading",
    "has_temperature_condition",
    # Parameter Inventory
    "ParameterRecord",
    "InventoryReport",
    "MappingStatus",
    "ExtractionStatus",
    "materialize_parameter_inventory",
]
