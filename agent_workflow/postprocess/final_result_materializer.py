"""
Shadow Final Result Materializer.

This module implements the Shadow Finalizer for Phase 4.1, which runs in parallel
with the official Step 3/4 pipeline without modifying the official outputs.

The Shadow Finalizer:
1. Materializes all 30 target fields from target_fields.yaml
2. Injects manufacturer from document_metadata
3. Merges conditions using monotonic merge rules
4. Preserves source Min/Typ/Max slots
5. Validates module_type semantic constraints
6. Generates shadow artifacts with full diff

Usage:
    finalizer = ShadowFinalizer(
        agent2_result=agent2_result,
        agent1_result=agent1_result,
        enriched_payload=enriched_payload,
        target_fields_config=target_fields,
    )
    
    # Shadow mode (default) - generates artifacts without modifying official outputs
    shadow_results = finalizer.run(mode=FinalizerMode.SHADOW)
    
    # Enforce mode - actually replaces official outputs
    final_results = finalizer.run(mode=FinalizerMode.ENFORCE)
"""

import json
from pathlib import Path
from typing import Any
from .finalizer_models import (
    ChangeType,
    ConditionSlot,
    FinalizedFieldResult,
    FinalizerDiff,
    FinalizerMode,
    FinalizerReport,
    RiskLevel,
    SourceValueSlots,
)
from .condition_merger import ConditionMerger, merge_final_conditions


# Default target fields config path
DEFAULT_TARGET_FIELDS_PATH = Path(__file__).parent.parent.parent / "config" / "target_fields.yaml"


class ShadowFinalizer:
    """
    Shadow Finalizer for materializing complete field results.
    
    This class processes Agent2Result and related artifacts to:
    1. Inject manufacturer from document_metadata
    2. Materialize all target fields (including missing ones)
    3. Merge conditions using monotonic rules
    4. Preserve source slots
    5. Validate semantic constraints
    6. Generate shadow artifacts with diff
    """
    
    def __init__(
        self,
        agent2_result: dict,
        agent1_result: dict,
        enriched_payload: dict,
        target_fields_config: list[dict] | None = None,
    ):
        """
        Initialize the Shadow Finalizer.
        
        Args:
            agent2_result: Agent2Result as dict (from step2 output)
            agent1_result: Agent1Result as dict (from step1 output)
            enriched_payload: EnrichedPayload as dict (from step0.5 output)
            target_fields_config: List of target field configs (from target_fields.yaml)
        """
        self.agent2_result = agent2_result
        self.agent1_result = agent1_result
        self.enriched_payload = enriched_payload
        
        # Parse target fields config
        self.target_fields = {}
        if target_fields_config:
            for field_config in target_fields_config:
                field_id = field_config.get("id")
                if field_id:
                    self.target_fields[field_id] = field_config
        
        # Build lookup structures
        self._build_lookups()
        
        # Results
        self.finalized_results: dict[str, FinalizedFieldResult] = {}
        self.diffs: list[FinalizerDiff] = []
        self.report = FinalizerReport()
    
    def _build_lookups(self):
        """Build lookup structures from Agent1 and Agent2 results."""
        
        # Agent2 params lookup by field_id
        self.agent2_params = {}
        for param in self.agent2_result.get("final_params", []):
            self.agent2_params[param["field_id"]] = param
        
        # Agent1 candidates lookup by field_id
        self.agent1_fields = {}
        for field in self.agent1_result.get("fields", []):
            field_id = field.get("field_id")
            if field_id:
                self.agent1_fields[field_id] = field
        
        # Document metadata
        self.document_metadata = self.enriched_payload.get("document_metadata", {})
        
        # Build lookup from (page_number, table_index, row_index) to enriched row
        self.enriched_row_lookup = {}
        for page in self.enriched_payload.get("pages", []):
            page_number = page.get("page_number")
            for table in page.get("tables", []):
                table_index = table.get("table_index")
                for row in table.get("rows", []):
                    row_index = row.get("row_index")
                    key = (page_number, table_index, row_index)
                    self.enriched_row_lookup[key] = row
        
        # Section titles detected (per-row, corresponds to enriched rows)
        self.section_titles = self.enriched_payload.get("section_titles_detected", [])
        
    def _get_field_config(self, field_id: str) -> dict | None:
        """Get the configuration for a target field."""
        return self.target_fields.get(field_id)
    
    def _extract_source_slots_from_row_cells(
        self,
        row_cells: list[str],
        field_config: dict | None = None,
    ) -> SourceValueSlots | None:
        """
        Extract Min/Typ/Max slots from row_cells based on column positions.
        
        The PDF table typically has columns like:
        | Symbol | Parameter | Min | Typ | Max | Unit | Condition |
        
        For most parameters:
        - Position 2 = Min (if numeric)
        - Position 3 = Typ (if numeric)
        - Position 4 = Max (if numeric)
        
        Returns:
            SourceValueSlots with values and evidence, or None if cannot determine
        """
        if not row_cells or len(row_cells) < 5:
            return None
        
        # Try to parse values from cells
        # Position 2 = Min, Position 3 = Typ, Position 4 = Max
        min_val = self._parse_numeric(row_cells[2]) if len(row_cells) > 2 else None
        typ_val = self._parse_numeric(row_cells[3]) if len(row_cells) > 3 else None
        max_val = self._parse_numeric(row_cells[4]) if len(row_cells) > 4 else None
        
        # Check if any value was found
        if min_val is None and typ_val is None and max_val is None:
            return None
        
        return SourceValueSlots(
            min=min_val,
            typ=typ_val,
            max=max_val,
            slot_evidence={
                "method": "column_position",
                "row_cells_preview": row_cells[:6],
            }
        )
    
    def _parse_numeric(self, s: str) -> float | None:
        """Parse a numeric string, returning None if not numeric."""
        if not s or s == "-" or s == "—" or s == "":
            return None
        try:
            # Remove any trailing units like "V", "mΩ", etc.
            s = s.strip()
            # Handle unicode minus
            s = s.replace("−", "-")
            return float(s)
        except ValueError:
            return None
    
    def _inject_manufacturer(self) -> tuple[FinalizedFieldResult, FinalizerDiff | None]:
        """
        Inject manufacturer from document_metadata as a formal field.
        
        Returns:
            Tuple of (FinalizedFieldResult, FinalizerDiff)
        """
        mfr_meta = self.document_metadata.get("manufacturer", {})
        status = mfr_meta.get("status")
        canonical_value = mfr_meta.get("canonical_value")
        
        if status == "resolved" and canonical_value:
            result = FinalizedFieldResult(
                field_id="manufacturer",
                status="final",
                value=canonical_value,
                source_type="document_metadata",
                confidence=0.95,
                reason=f"Injected from document_metadata (status={status})",
                metadata_evidence=mfr_meta.get("evidences", []),
                change_type=ChangeType.METADATA_INJECTED,
            )
            
            diff = FinalizerDiff(
                field_id="manufacturer",
                change_type=ChangeType.METADATA_INJECTED,
                before={"status": "not_in_agent2"},
                after={"status": "final", "value": canonical_value},
                reason="Manufacturer injected from document_metadata",
                evidence=[f"status={status}", f"canonical_value={canonical_value}"],
                risk_level=RiskLevel.LOW,
            )
            
            return result, diff
        
        elif status == "ambiguous":
            result = FinalizedFieldResult(
                field_id="manufacturer",
                status="review_needed",
                source_type="document_metadata",
                confidence=0.5,
                reason=f"Ambiguous manufacturer in metadata",
                metadata_evidence=mfr_meta.get("evidences", []),
                change_type=ChangeType.METADATA_INJECTED,
            )
            
            diff = FinalizerDiff(
                field_id="manufacturer",
                change_type=ChangeType.METADATA_INJECTED,
                before={"status": "not_in_agent2"},
                after={"status": "review_needed", "reason": "ambiguous metadata"},
                reason="Manufacturer metadata is ambiguous",
                risk_level=RiskLevel.MEDIUM,
            )
            
            return result, diff
        
        else:
            result = FinalizedFieldResult(
                field_id="manufacturer",
                status="missing",
                source_type="document_metadata",
                missing_reason="metadata_missing",
                search_completed=True,
                reason="No manufacturer found in document_metadata",
                change_type=ChangeType.METADATA_INJECTED,
            )
            
            diff = FinalizerDiff(
                field_id="manufacturer",
                change_type=ChangeType.METADATA_INJECTED,
                before={"status": "not_in_agent2"},
                after={"status": "missing", "reason": "no metadata"},
                reason="No manufacturer in document_metadata",
                risk_level=RiskLevel.LOW,
            )
            
            return result, diff
    
    def _process_agent2_field(
        self,
        field_id: str,
        agent2_param: dict,
        field_config: dict | None,
    ) -> tuple[FinalizedFieldResult, list[FinalizerDiff]]:
        """
        Process a field that was returned by Agent2.
        
        This method:
        1. Preserves Agent2 values
        2. Merges conditions using monotonic rules
        3. Extracts and preserves source slots
        4. Validates semantic constraints
        
        Returns:
            Tuple of (FinalizedFieldResult, list of diffs)
        """
        diffs = []
        
        # Get Agent1 candidates for this field
        agent1_field = self.agent1_fields.get(field_id, {})
        selected_candidate = agent1_field.get("selected_candidate", {})
        row_cells = selected_candidate.get("row_cells", [])
        
        # Get resolved_condition from enriched row lookup
        resolved_condition = None
        enriched_row = None
        source_row_id = None
        
        source_page = selected_candidate.get("source_page")
        source_table_index = selected_candidate.get("table_index")
        source_row_index = selected_candidate.get("row_index")
        
        if source_page is not None and source_table_index is not None and source_row_index is not None:
            key = (source_page, source_table_index, source_row_index)
            enriched_row = self.enriched_row_lookup.get(key)
            if enriched_row:
                resolved_condition = enriched_row.get("resolved_condition")
                source_row_id = enriched_row.get("row_id")
        
        # Agent2 condition
        agent2_condition = agent2_param.get("condition")
        
        # Merge conditions using monotonic merge
        merger = ConditionMerger()
        merge_result = merger.merge(
            resolved_condition=resolved_condition,
            agent2_condition=agent2_condition,
            agent2_has_explicit_evidence=True,  # Agent2 has row evidence
            agent2_row_id=source_row_id,
        )
        
        # Check if condition was restored from resolved
        condition_changed = False
        if resolved_condition and agent2_condition:
            # Check if Agent2 condition is shorter than resolved
            if len(agent2_condition) < len(resolved_condition):
                # Agent2 condition shorter - check if resolved keys are preserved
                if merge_result.deleted_keys:
                    condition_changed = True
        elif resolved_condition and not agent2_condition:
            # Agent2 has no condition but resolved has one
            condition_changed = True
        
        # Determine the final condition
        final_condition = agent2_condition if agent2_condition else resolved_condition
        if merge_result.merged_condition:
            final_condition = merge_result.merged_condition
        
        result = FinalizedFieldResult(
            field_id=field_id,
            status=agent2_param.get("status", "missing"),
            value=agent2_param.get("value"),
            min=agent2_param.get("min"),
            typ=agent2_param.get("typ"),
            max=agent2_param.get("max"),
            unit=agent2_param.get("unit"),
            condition=final_condition,
            resolved_condition=resolved_condition,
            agent2_condition=agent2_condition,
            merged_conditions=merge_result.condition_slots,
            source_type="agent2",
            source_row_id=source_row_id,
            confidence=agent2_param.get("confidence", 0.0),
            reason=agent2_param.get("reason", ""),
            warnings=agent2_param.get("warnings", []),
            change_type=ChangeType.UNCHANGED,
        )
        
        # Create condition restoration or conflict diff
        if condition_changed:
            if merge_result.conflicts:
                # There are conflicts
                for conflict in merge_result.conflicts:
                    if conflict.get("resolution") == "kept_resolved":
                        # Resolved was kept, create a condition_restored diff
                        diff = FinalizerDiff(
                            field_id=field_id,
                            change_type=ChangeType.CONDITION_RESTORED,
                            before={"condition": agent2_condition or ""},
                            after={"condition": final_condition},
                            reason=f"Condition restored from resolved: {conflict.get('key')}={conflict.get('resolved_value')} kept (Agent2 had {conflict.get('agent2_value') or 'none'})",
                            source_row_id=source_row_id,
                            evidence=[str(conflict)],
                            risk_level=RiskLevel.MEDIUM,
                        )
                        diffs.append(diff)
                        result.change_type = ChangeType.CONDITION_RESTORED
            elif resolved_condition and not agent2_condition:
                # Agent2 had no condition, resolved has one - restore
                diff = FinalizerDiff(
                    field_id=field_id,
                    change_type=ChangeType.CONDITION_RESTORED,
                    before={"condition": ""},
                    after={"condition": final_condition},
                    reason="Condition restored from resolved (Agent2 had no condition)",
                    source_row_id=source_row_id,
                    evidence=[f"resolved={resolved_condition}"],
                    risk_level=RiskLevel.LOW,
                )
                diffs.append(diff)
                result.change_type = ChangeType.CONDITION_RESTORED
        
        # Extract source slots from row_cells
        source_slots = self._extract_source_slots_from_row_cells(row_cells, field_config)
        if source_slots and source_slots.has_any_value():
            result.source_value_slots = source_slots
            
            # Check if Agent2 values match source slots
            if self._check_slot_discrepancy(result, source_slots):
                # Agent2 put value in wrong slot - restore from source
                diff = self._create_slot_restoration_diff(
                    field_id, result, source_slots, agent2_param
                )
                if diff:
                    diffs.append(diff)
        
        # Apply semantic validation for module_type
        if field_id == "module_type":
            semantic_diff = self._validate_module_type_semantic(result, agent1_field)
            if semantic_diff:
                diffs.append(semantic_diff)
        
        return result, diffs
    
    def _check_slot_discrepancy(
        self,
        result: FinalizedFieldResult,
        source_slots: SourceValueSlots,
    ) -> bool:
        """
        Check if there's a discrepancy between Agent2 values and source slots.
        
        Returns True if there's a discrepancy that should be corrected.
        """
        if not source_slots.has_any_value():
            return False
        
        # Check if source has explicit Min slot value
        if source_slots.min is not None:
            # Source has Min value
            if result.min is None and source_slots.min == result.value:
                # Agent2 put source min in "value" instead of "min"
                return True
        
        return False
    
    def _create_slot_restoration_diff(
        self,
        field_id: str,
        result: FinalizedFieldResult,
        source_slots: SourceValueSlots,
        agent2_param: dict,
    ) -> FinalizerDiff | None:
        """
        Create a diff for slot restoration.
        """
        before = {
            "min": agent2_param.get("min"),
            "typ": agent2_param.get("typ"),
            "max": agent2_param.get("max"),
            "value": agent2_param.get("value"),
        }
        
        # Restore from source slots
        result.min = source_slots.min
        result.typ = source_slots.typ
        result.max = source_slots.max
        # Keep value as first non-None or None
        result.value = None
        result.change_type = ChangeType.SOURCE_SLOT_RESTORED
        
        after = {
            "min": result.min,
            "typ": result.typ,
            "max": result.max,
            "value": result.value,
        }
        
        return FinalizerDiff(
            field_id=field_id,
            change_type=ChangeType.SOURCE_SLOT_RESTORED,
            before=before,
            after=after,
            reason="Agent2 placed source min in 'value' slot instead of 'min'. Restored from source.",
            source_row_id=result.source_row_id,
            evidence=[
                f"source_slots.min={source_slots.min}",
                f"source_slots.typ={source_slots.typ}",
                f"source_slots.max={source_slots.max}",
            ],
            risk_level=RiskLevel.MEDIUM,
        )
    
    def _validate_module_type_semantic(
        self,
        result: FinalizedFieldResult,
        agent1_field: dict,
    ) -> FinalizerDiff | None:
        """
        Validate module_type against semantic constraints.
        
        Constraints:
        - type: short_code
        - max_length: 24
        - reject_commas: true
        - reject_sentence: true
        
        If current value violates constraints, mark as rejected and try to find better candidate.
        """
        value = result.value or ""
        
        # Check constraints
        violations = []
        if len(value) > 24:
            violations.append(f"exceeds max_length (24): {len(value)}")
        if "," in value:
            violations.append("contains comma (appears to be a description)")
        if len(value.split()) > 5:
            violations.append("appears to be a sentence (>5 words)")
        
        if not violations:
            return None
        
        # Value violates semantic constraints
        result.semantic_rejected = True
        result.semantic_rejection_reason = "; ".join(violations)
        result.status = "review_needed"
        result.change_type = ChangeType.SEMANTIC_VALUE_REJECTED
        
        before = {"value": value, "status": "final"}
        after = {"value": value, "status": "review_needed", "reason": result.semantic_rejection_reason}
        
        # Try to find a better candidate from Agent1
        better_candidate = self._find_better_module_type_candidate(agent1_field)
        if better_candidate:
            result.value = better_candidate["value"]
            result.confidence = better_candidate.get("confidence", 0.7)
            result.source_row_id = better_candidate.get("row_id")
            result.change_type = ChangeType.SEMANTIC_CANDIDATE_REPLACED
            after = {
                "value": result.value,
                "status": "review_needed",
                "reason": f"replaced with better candidate: {result.semantic_rejection_reason}",
            }
        
        return FinalizerDiff(
            field_id="module_type",
            change_type=result.change_type,
            before=before,
            after=after,
            reason=f"module_type value violates semantic constraints: {result.semantic_rejection_reason}",
            source_row_id=result.source_row_id,
            evidence=violations,
            risk_level=RiskLevel.MEDIUM,
        )
    
    def _find_better_module_type_candidate(
        self,
        agent1_field: dict,
    ) -> dict | None:
        """
        Find a better module_type candidate from Agent1 candidates.
        
        Look for candidates that match short_code constraints:
        - Short (<=24 chars)
        - No commas
        - Likely a module type code (ME3, etc.)
        """
        candidates = agent1_field.get("candidates", [])
        
        short_code_candidates = []
        for c in candidates:
            val = c.get("value") or ""
            if not val:
                row_cells = c.get("row_cells", [])
                if len(row_cells) >= 3:
                    val = str(row_cells[1]).strip()  # Usually parameter name is in col 1
            
            if val and len(val) <= 24 and "," not in val:
                # Check if it looks like a module type code (not a full description)
                if any(x in val.upper() for x in ["ME", "MG", "MODULE", "PACKAGE"]):
                    if len(val.split()) <= 2:  # Short phrase, not a sentence
                        short_code_candidates.append({
                            "value": val,
                            "confidence": c.get("confidence", 0.7),
                            "row_id": f"page_{c.get('source_page')}_row_{c.get('row_index')}",
                        })
        
        if short_code_candidates:
            # Return the highest confidence candidate
            return max(short_code_candidates, key=lambda x: x.get("confidence", 0))
        
        return None
    
    def _materialize_missing_field(
        self,
        field_id: str,
        field_config: dict | None,
    ) -> tuple[FinalizedFieldResult, FinalizerDiff]:
        """
        Materialize a missing field with structured placeholder.
        
        Only converts to valid_missing if search_completed=True and candidate_count=0.
        """
        # Check if there are candidates in Agent1
        agent1_field = self.agent1_fields.get(field_id, {})
        candidates = agent1_field.get("candidates", [])
        candidate_count = len(candidates)
        
        result = FinalizedFieldResult(
            field_id=field_id,
            status="missing",
            missing_reason="not_returned_by_agent",
            search_completed=True,
            candidate_count=candidate_count,
            source_type="missing",
            confidence=0.0,
            reason=f"Field not returned by Agent2. Found {candidate_count} candidates in Agent1.",
            change_type=ChangeType.MISSING_FIELD_MATERIALIZED,
        )
        
        # If no candidates and search completed, it could be valid_missing
        if candidate_count == 0:
            result.status = "valid_missing"
            result.missing_reason = "not_explicitly_specified"
            result.change_type = ChangeType.MISSING_FIELD_MATERIALIZED
        
        before = {"status": "not_in_agent2"}
        after = {
            "status": result.status,
            "missing_reason": result.missing_reason,
            "candidate_count": candidate_count,
        }
        
        diff = FinalizerDiff(
            field_id=field_id,
            change_type=ChangeType.MISSING_FIELD_MATERIALIZED,
            before=before,
            after=after,
            reason=f"Materialized missing field (candidate_count={candidate_count})",
            risk_level=RiskLevel.LOW,
        )
        
        return result, diff
    
    def run(self, mode: FinalizerMode = FinalizerMode.SHADOW) -> dict:
        """
        Run the Shadow Finalizer.
        
        Args:
            mode: FinalizerMode.OFF, SHADOW, or ENFORCE
            
        Returns:
            Dict with finalized_results, report, and diffs
        """
        if mode == FinalizerMode.OFF:
            return {
                "finalized_results": {},
                "report": FinalizerReport().to_dict(),
                "diffs": [],
                "mode": "off",
            }
        
        self.finalized_results = {}
        self.diffs = []
        
        # Initialize report
        self.report = FinalizerReport()
        self.report.total_target_fields = len(self.target_fields)
        
        # Step 1: Inject manufacturer from metadata
        mfr_result, mfr_diff = self._inject_manufacturer()
        self.finalized_results["manufacturer"] = mfr_result
        if mfr_diff:
            self.diffs.append(mfr_diff)
            self.report.metadata_injections += 1
        
        # Step 2: Process all Agent2 fields
        for field_id, agent2_param in self.agent2_params.items():
            if field_id == "manufacturer":
                continue  # Already handled
            
            field_config = self._get_field_config(field_id)
            result, diffs = self._process_agent2_field(field_id, agent2_param, field_config)
            self.finalized_results[field_id] = result
            self.diffs.extend(diffs)
            
            if diffs:
                self.report.materialized_fields += 1
                for d in diffs:
                    if d.change_type == ChangeType.SOURCE_SLOT_RESTORED:
                        self.report.slots_restored += 1
                    elif d.change_type == ChangeType.SEMANTIC_VALUE_REJECTED:
                        self.report.semantic_rejections += 1
                        self.report.review_needed_created += 1
                    elif d.change_type == ChangeType.SEMANTIC_CANDIDATE_REPLACED:
                        self.report.review_needed_created += 1
            else:
                self.report.unchanged_fields += 1
        
        self.report.agent2_returned_fields = len(self.agent2_params)
        
        # Step 3: Materialize missing fields
        for field_id in self.target_fields.keys():
            if field_id in self.finalized_results:
                continue
            if field_id == "manufacturer":
                continue  # Already handled
            
            field_config = self._get_field_config(field_id)
            result, diff = self._materialize_missing_field(field_id, field_config)
            self.finalized_results[field_id] = result
            self.diffs.append(diff)
            self.report.materialized_fields += 1
            self.report.valid_missing_created += 1
        
        # Count high risk changes
        for d in self.diffs:
            if d.risk_level == RiskLevel.HIGH:
                self.report.high_risk_changes += 1
        
        # Update report diffs
        self.report.diffs = self.diffs
        
        # Generate output
        finalized_dict = {
            field_id: result.to_dict()
            for field_id, result in self.finalized_results.items()
        }
        
        return {
            "finalized_results": finalized_dict,
            "report": self.report.to_dict(),
            "diffs": [d.to_dict() for d in self.diffs],
            "mode": mode.value,
        }


def load_target_fields_config(config_path: Path = DEFAULT_TARGET_FIELDS_PATH) -> list[dict]:
    """Load target fields configuration from YAML file."""
    import yaml
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return config.get("fields", [])
