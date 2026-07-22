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

        # Build table header lookup: (page_number, table_index) -> header_cells
        self.table_header_lookup = {}
        for page in self.enriched_payload.get("pages", []):
            page_number = page.get("page_number")
            for table in page.get("tables", []):
                table_index = table.get("table_index")
                rows = table.get("rows", [])
                if rows:
                    # First row is typically the header - use raw_cells field
                    header_cells = rows[0].get("raw_cells", [])
                    self.table_header_lookup[(page_number, table_index)] = header_cells

        # Section titles detected (per-row, corresponds to enriched rows)
        self.section_titles = self.enriched_payload.get("section_titles_detected", [])

    def _get_field_config(self, field_id: str) -> dict | None:
        """Get the configuration for a target field."""
        return self.target_fields.get(field_id)

    def _get_table_header(self, page_number: int, table_index: int) -> list[str]:
        """Get table header cells for a given page and table."""
        return self.table_header_lookup.get((page_number, table_index), [])

    def _detect_table_schema(self, table_header: list[str]) -> dict:
        """
        Detect table schema from header cells.

        Returns:
            dict with keys:
            - type: "values" | "min_typ_max" | "unknown"
            - column_roles: dict mapping position -> role name
        """
        if not table_header:
            return {"type": "unknown", "column_roles": {}}

        # Normalize header cells to lowercase
        header_lower = [h.lower().strip() for h in table_header]

        # Check for "Values" table (single value column)
        # Pattern: Symbol | Parameter | Values | '' | '' | Unit | Test Conditions
        has_values = any('values' in h for h in header_lower)
        has_min_typ_max = any('min' in h or 'typ' in h or 'max' in h for h in header_lower)

        if has_values and not has_min_typ_max:
            # "Values" table - single value column
            column_roles = {}
            for i, h in enumerate(header_lower):
                if 'symbol' in h:
                    column_roles[i] = 'symbol'
                elif 'parameter' in h or 'param' in h:
                    column_roles[i] = 'parameter'
                elif 'values' in h:
                    column_roles[i] = 'value'  # Single value column
                elif 'unit' in h:
                    column_roles[i] = 'unit'
                elif 'test' in h or 'condition' in h:
                    column_roles[i] = 'condition'
            return {"type": "values", "column_roles": column_roles}

        if has_min_typ_max:
            # Min/Typ/Max table
            column_roles = {}
            for i, h in enumerate(header_lower):
                if 'symbol' in h:
                    column_roles[i] = 'symbol'
                elif 'parameter' in h or 'param' in h:
                    column_roles[i] = 'parameter'
                elif 'min' in h:
                    column_roles[i] = 'min'
                elif 'typ' in h:
                    column_roles[i] = 'typ'
                elif 'max' in h:
                    column_roles[i] = 'max'
                elif 'unit' in h:
                    column_roles[i] = 'unit'
                elif 'test' in h or 'condition' in h:
                    column_roles[i] = 'condition'
            return {"type": "min_typ_max", "column_roles": column_roles}

        return {"type": "unknown", "column_roles": {}}

    def _extract_source_slots_from_row_cells(
        self,
        row_cells: list[str],
        field_config: dict | None = None,
        table_header: list[str] | None = None,
    ) -> SourceValueSlots | None:
        """
        Extract Min/Typ/Max/Value slots from row_cells based on table header.

        For "Values" tables (Symbol | Parameter | Values | '' | '' | Unit | Test Conditions):
        - Position 2 = value (single value column, NOT min)

        For Min/Typ/Max tables (Symbol | Parameter | Min | Typ | Max | Unit | Test Conditions):
        - Position 2 = Min
        - Position 3 = Typ
        - Position 4 = Max

        Returns:
            SourceValueSlots with values and evidence, or None if cannot determine
        """
        if not row_cells or len(row_cells) < 5:
            return None

        # Detect table schema from header
        schema = self._detect_table_schema(table_header or [])
        column_roles = schema.get("column_roles", {})

        # Extract values based on column roles
        min_val = None
        typ_val = None
        max_val = None
        value_val = None

        if schema["type"] == "values":
            # Single value column table
            for i, val in enumerate(row_cells):
                role = column_roles.get(i)
                if role == 'value':
                    value_val = self._parse_numeric(val)
        elif schema["type"] == "min_typ_max":
            # Min/Typ/Max table
            for i, val in enumerate(row_cells):
                role = column_roles.get(i)
                if role == 'min':
                    min_val = self._parse_numeric(val)
                elif role == 'typ':
                    typ_val = self._parse_numeric(val)
                elif role == 'max':
                    max_val = self._parse_numeric(val)
        else:
            # Unknown schema - fallback to original logic
            min_val = self._parse_numeric(row_cells[2]) if len(row_cells) > 2 else None
            typ_val = self._parse_numeric(row_cells[3]) if len(row_cells) > 3 else None
            max_val = self._parse_numeric(row_cells[4]) if len(row_cells) > 4 else None

        # Check if any value was found
        if min_val is None and typ_val is None and max_val is None and value_val is None:
            return None

        return SourceValueSlots(
            min=min_val,
            typ=typ_val,
            max=max_val,
            value=value_val,
            schema_type=schema["type"],
            slot_evidence={
                "method": "table_header_based",
                "schema_type": schema["type"],
                "column_roles": {str(k): v for k, v in column_roles.items()},
                "row_cells_preview": row_cells[:6],
            }
        )

    def _parse_numeric(self, s: str) -> float | None:
        """Parse a numeric string, returning None if not numeric."""
        if not s or s == "-" or s == "-" or s == "":
            return None
        try:
            # Remove any trailing units like "V", "mΩ", etc.
            s = s.strip()
            # Handle unicode minus
            s = s.replace("-", "-")
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
        # Handle selected_candidate being None
        raw_selected_candidate = agent1_field.get("selected_candidate") if agent1_field else None
        selected_candidate = raw_selected_candidate if raw_selected_candidate else {}
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

        # Extract source slots from row_cells using table header
        table_header = self._get_table_header(source_page, source_table_index) if source_page is not None else []
        source_slots = self._extract_source_slots_from_row_cells(row_cells, field_config, table_header)
        if source_slots and source_slots.has_any_value():
            result.source_value_slots = source_slots

            # Check if Agent2 values match source slots (skip for "values" schema - Agent2 may be correct)
            if source_slots.schema_type != "values" and self._check_slot_discrepancy(result, source_slots):
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

        # Apply priority validation for part_number (prefer Order Number over Marking)
        if field_id == "part_number":
            part_num_diff = self._validate_part_number_priority(result, agent1_field)
            if part_num_diff:
                diffs.append(part_num_diff)

        return result, diffs

    def _check_slot_discrepancy(
        self,
        result: FinalizedFieldResult,
        source_slots: SourceValueSlots,
    ) -> bool:
        """
        Check if there's a discrepancy between Agent2 values and source slots.

        For Min/Typ/Max tables:
        - If source has min value and Agent2 didn't put it in min slot, that's a discrepancy
        - If source has typ value and Agent2 didn't put it in typ slot, that's a discrepancy
        - If source has max value and Agent2 didn't put it in max slot, that's a discrepancy

        Returns True if there's a discrepancy that should be corrected.
        """
        if not source_slots.has_any_value():
            return False

        # For Min/Typ/Max tables, check each slot
        if source_slots.schema_type == "min_typ_max":
            # Check Min slot
            if source_slots.min is not None:
                if result.min != source_slots.min:
                    # Source has min but Agent2 didn't put it in min slot
                    # Check if Agent2 put it in value or typ or max
                    if result.value == source_slots.min or result.typ == source_slots.min or result.max == source_slots.min:
                        return True

            # Check Typ slot
            if source_slots.typ is not None:
                if result.typ != source_slots.typ:
                    # Source has typ but Agent2 didn't put it in typ slot
                    if result.value == source_slots.typ or result.min == source_slots.typ or result.max == source_slots.typ:
                        return True

            # Check Max slot
            if source_slots.max is not None:
                if result.max != source_slots.max:
                    # Source has max but Agent2 didn't put it in max slot
                    if result.value == source_slots.max or result.min == source_slots.max or result.typ == source_slots.max:
                        return True

        # Legacy check for "values" tables or unknown schema - only check min->value case
        if source_slots.min is not None:
            if result.min is None and source_slots.min == result.value:
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

        For "values" tables:
        - Source value goes to result.value
        - Clear min/typ/max

        For "min_typ_max" tables:
        - Restore min/typ/max from source
        - result.value unchanged
        """
        before = {
            "min": agent2_param.get("min"),
            "typ": agent2_param.get("typ"),
            "max": agent2_param.get("max"),
            "value": agent2_param.get("value"),
        }

        schema_type = source_slots.schema_type

        if schema_type == "values":
            # For values table, restore value from source
            result.value = source_slots.value
            result.min = None
            result.typ = None
            result.max = None
            reason = "Agent2 placed source value in wrong slot (min/typ/max). Restored to 'value' slot."
        elif schema_type == "min_typ_max":
            # For min_typ_max table, restore min/typ/max from source
            result.min = source_slots.min
            result.typ = source_slots.typ
            result.max = source_slots.max
            # Determine which slot was wrong
            wrong_slots = []
            if source_slots.min is not None and agent2_param.get("min") != source_slots.min:
                wrong_slots.append(f"min: expected {source_slots.min}, got {agent2_param.get('min')}")
            if source_slots.typ is not None and agent2_param.get("typ") != source_slots.typ:
                wrong_slots.append(f"typ: expected {source_slots.typ}, got {agent2_param.get('typ')}")
            if source_slots.max is not None and agent2_param.get("max") != source_slots.max:
                wrong_slots.append(f"max: expected {source_slots.max}, got {agent2_param.get('max')}")
            reason = f"Agent2 placed source values in wrong slots. Restored from source: {', '.join(wrong_slots)}"
        else:
            # Fallback - original behavior
            result.min = source_slots.min
            result.typ = source_slots.typ
            result.max = source_slots.max
            result.value = None
            reason = "Agent2 placed source min in wrong slot. Restored from source."

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
            reason=reason,
            source_row_id=result.source_row_id,
            evidence=[
                f"schema_type={schema_type}",
                f"source_slots.value={source_slots.value}",
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
        Find a better module_type candidate from Agent1 candidates AND enriched_payload.

        Search order:
        1. Agent1 selected/retained candidates (existing logic)
        2. EnrichedPayload rows with row_type=unknown matching preferred_labels

        Preferred labels: Package Type, Module Type, Package
        Excluded labels: Description, Product Description, General Description
        """
        preferred_labels = ["package type", "module type", "package"]
        excluded_labels = ["description", "product description", "general description"]

        short_code_candidates = []

        # 1. Search Agent1 candidates (existing logic)
        candidates = agent1_field.get("candidates", [])
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
                            "source": "agent1",
                        })

        # 2. Search enriched_payload for Package Type rows (row_type=unknown)
        for page in self.enriched_payload.get("pages", []):
            for table in page.get("tables", []):
                for row in table.get("rows", []):
                    row_type = row.get("row_type", "")
                    # Search in unknown and parameter rows
                    if row_type not in ["unknown", "parameter"]:
                        continue

                    raw_cells = row.get("raw_cells", [])
                    if len(raw_cells) < 2:
                        continue

                    # Check if this row matches preferred labels
                    label = str(raw_cells[0]).lower().strip()
                    if not any(pl in label for pl in preferred_labels):
                        continue

                    # Check if excluded labels appear
                    if any(el in label for el in excluded_labels):
                        continue

                    # Get the value (usually in col 1)
                    val = str(raw_cells[1]).strip() if len(raw_cells) > 1 else ""

                    if not val:
                        continue

                    # Apply semantic constraints
                    if len(val) > 24 or "," in val:
                        continue

                    # Looks like a valid module type code
                    short_code_candidates.append({
                        "value": val,
                        "confidence": 0.8,  # Slightly lower than Agent1
                        "row_id": row.get("row_id"),
                        "source": "enriched_payload",
                        "page": row.get("page_number"),
                        "table": row.get("table_index"),
                        "row_idx": row.get("row_index"),
                    })

        if short_code_candidates:
            # Return the highest confidence candidate
            return max(short_code_candidates, key=lambda x: x.get("confidence", 0))

        return None

    def _validate_part_number_priority(
        self,
        result: FinalizedFieldResult,
        agent1_field: dict,
    ) -> FinalizerDiff | None:
        """
        Validate that part_number prefers Order Number over Marking.

        If the selected candidate is from a "Marking" row but an "Order Number" candidate
        exists in the candidates list, replace the Marking value with Order Number.
        """
        # Get the selected candidate's row_cells
        selected_candidate = agent1_field.get("selected_candidate", {})
        row_cells = selected_candidate.get("row_cells", [])

        if not row_cells:
            return None

        # Check if the selected candidate is a Marking row (case-insensitive)
        label = str(row_cells[0]).strip().lower()
        if label != "marking":
            return None

        # Search all candidates for Order Number
        candidates = agent1_field.get("candidates", [])
        order_number_candidate = None

        for c in candidates:
            cells = c.get("row_cells", [])
            if len(cells) >= 2:
                cell_label = str(cells[0]).strip().lower()
                if "order number" in cell_label:
                    order_number_candidate = c
                    break

        if not order_number_candidate:
            return None

        # Get the Order Number value (usually in col 1)
        cells = order_number_candidate.get("row_cells", [])
        order_number_value = str(cells[1]).strip() if len(cells) > 1 else ""

        if not order_number_value:
            return None

        # Replace the value with Order Number
        old_value = result.value
        result.value = order_number_value
        result.confidence = order_number_candidate.get("confidence", 0.8)
        result.source_row_id = f"p{order_number_candidate.get('source_page')}_t{order_number_candidate.get('table_index')}_r{order_number_candidate.get('row_index')}"
        result.change_type = ChangeType.SEMANTIC_CANDIDATE_REPLACED

        before = {"value": old_value, "status": "final"}
        after = {
            "value": order_number_value,
            "status": "review_needed",
            "reason": "preferred Order Number over Marking",
        }

        return FinalizerDiff(
            field_id="part_number",
            change_type=ChangeType.SEMANTIC_CANDIDATE_REPLACED,
            before=before,
            after=after,
            reason="part_number: Order Number preferred over Marking (semantic priority)",
            source_row_id=result.source_row_id,
            evidence=[
                f"Marking row had: {old_value}",
                f"Order Number row has: {order_number_value}",
            ],
            risk_level=RiskLevel.LOW,
        )

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
