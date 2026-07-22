"""
Data models for the Shadow Finalizer.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FinalizerMode(str, Enum):
    """Finalizer operation mode."""
    OFF = "off"
    SHADOW = "shadow"
    ENFORCE = "enforce"


class ChangeType(str, Enum):
    """Type of change made by the finalizer."""
    METADATA_INJECTED = "metadata_injected"
    MISSING_FIELD_MATERIALIZED = "missing_field_materialized"
    CONDITION_RESTORED = "condition_restored"
    CONDITION_CONFLICT = "condition_conflict"
    SOURCE_SLOT_RESTORED = "source_slot_restored"
    SEMANTIC_VALUE_REJECTED = "semantic_value_rejected"
    SEMANTIC_CANDIDATE_REPLACED = "semantic_candidate_replaced"
    UNCHANGED = "unchanged"


class RiskLevel(str, Enum):
    """Risk level of a change."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class SourceValueSlots:
    """
    Preserves the original source column slots (Min/Typ/Max) from the PDF table.
    
    This ensures we don't lose the original column positions when Agent 2
    re-expresses values in different slots.
    """
    value: float | None = None
    min: float | None = None
    typ: float | None = None
    max: float | None = None
    slot_evidence: dict[str, Any] = field(default_factory=dict)
    
    def has_any_value(self) -> bool:
        return any(v is not None for v in [self.value, self.min, self.typ, self.max])
    
    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "min": self.min,
            "typ": self.typ,
            "max": self.max,
            "slot_evidence": self.slot_evidence,
        }


@dataclass
class ConditionSlot:
    """A single key=value condition pair."""
    key: str
    value: str
    source: str = "resolved"  # "resolved" or "agent2"
    evidence: str = ""


@dataclass
class FinalizedFieldResult:
    """
    A finalized field result after Shadow Finalizer processing.
    
    This represents the best-effort extraction of a field value with
    full audit trail.
    """
    field_id: str
    status: str  # "final", "review_needed", "missing", "valid_missing", "blocked"
    
    # Value slots
    value: float | None = None
    min: float | None = None
    typ: float | None = None
    max: float | None = None
    unit: str | None = None
    
    # Condition
    condition: str | None = None
    resolved_condition: str | None = None  # From Step 0.5
    agent2_condition: str | None = None  # From Agent 2
    merged_conditions: list[ConditionSlot] = field(default_factory=list)
    
    # Source tracking
    source_type: str | None = None  # "document_metadata", "agent2", "candidate", "missing"
    source_row_id: str | None = None
    source_value_slots: SourceValueSlots | None = None
    
    # Quality
    confidence: float = 0.0
    reason: str = ""
    warnings: list[str] = field(default_factory=list)
    
    # Missing field tracking
    missing_reason: str | None = None
    search_completed: bool = False
    candidate_count: int | None = None
    extraction_errors: list[str] = field(default_factory=list)
    
    # Semantic validation
    semantic_rejected: bool = False
    semantic_rejection_reason: str = ""
    slot_ambiguous: bool = False
    
    # Metadata
    metadata_evidence: list[dict] = field(default_factory=list)
    change_type: ChangeType | None = None
    
    def to_dict(self) -> dict:
        return {
            "field_id": self.field_id,
            "status": self.status,
            "value": self.value,
            "min": self.min,
            "typ": self.typ,
            "max": self.max,
            "unit": self.unit,
            "condition": self.condition,
            "resolved_condition": self.resolved_condition,
            "agent2_condition": self.agent2_condition,
            "merged_conditions": [
                {"key": c.key, "value": c.value, "source": c.source}
                for c in self.merged_conditions
            ],
            "source_type": self.source_type,
            "source_row_id": self.source_row_id,
            "source_value_slots": self.source_value_slots.to_dict() if self.source_value_slots else None,
            "confidence": self.confidence,
            "reason": self.reason,
            "warnings": self.warnings,
            "missing_reason": self.missing_reason,
            "search_completed": self.search_completed,
            "candidate_count": self.candidate_count,
            "extraction_errors": self.extraction_errors,
            "semantic_rejected": self.semantic_rejected,
            "semantic_rejection_reason": self.semantic_rejection_reason,
            "slot_ambiguous": self.slot_ambiguous,
            "metadata_evidence": self.metadata_evidence,
            "change_type": self.change_type.value if self.change_type else None,
        }


@dataclass
class FinalizerDiff:
    """
    Represents a single change made by the finalizer.
    """
    field_id: str
    change_type: ChangeType
    before: dict
    after: dict
    reason: str
    source_row_id: str | None = None
    evidence: list[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    
    def to_dict(self) -> dict:
        return {
            "field_id": self.field_id,
            "change_type": self.change_type.value,
            "before": self.before,
            "after": self.after,
            "reason": self.reason,
            "source_row_id": self.source_row_id,
            "evidence": self.evidence,
            "risk_level": self.risk_level.value,
        }


@dataclass
class FinalizerReport:
    """
    Complete report of the Shadow Finalizer run.
    """
    total_target_fields: int = 0
    agent2_returned_fields: int = 0
    materialized_fields: int = 0
    metadata_injections: int = 0
    conditions_restored: int = 0
    condition_conflicts: int = 0
    slots_restored: int = 0
    semantic_rejections: int = 0
    review_needed_created: int = 0
    valid_missing_created: int = 0
    high_risk_changes: int = 0
    unchanged_fields: int = 0
    
    diffs: list[FinalizerDiff] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "total_target_fields": self.total_target_fields,
            "agent2_returned_fields": self.agent2_returned_fields,
            "materialized_fields": self.materialized_fields,
            "metadata_injections": self.metadata_injections,
            "conditions_restored": self.conditions_restored,
            "condition_conflicts": self.condition_conflicts,
            "slots_restored": self.slots_restored,
            "semantic_rejections": self.semantic_rejections,
            "review_needed_created": self.review_needed_created,
            "valid_missing_created": self.valid_missing_created,
            "high_risk_changes": self.high_risk_changes,
            "unchanged_fields": self.unchanged_fields,
            "diffs": [d.to_dict() for d in self.diffs],
        }
