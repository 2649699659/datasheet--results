"""
shared_condition_propagator.py — Phase 3A: Shared condition propagation.

This module implements conservative shared test condition propagation for
contiguous parameter rows within the same Camelot table and section.

IMPORTANT: Without cell-level coordinate evidence, this is INFERRED shared
condition propagation, NOT confirmed merged cell recovery. We conservatively
propagate conditions only when the evidence is strong.

Rules:
- Same page
- Same table
- Same section (or both without section_title)
- Contiguous PARAMETER rows
- Source row has meaningful test conditions (not just TC/TJ)
- Target row has empty raw_condition
- Propagation distance <= max_rows
- Stops at any non-PARAMETER row
- Does NOT propagate to Module Physical Characteristics

Condition priority (highest to lowest):
1. Current row raw_condition
2. Shared condition from same group
3. Page heading condition (TJ=25°C)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .models import EnrichedPayload, EnrichedTable, EnrichedRow, RowType, ContextStatus


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_CONFIG = {
    "enabled": True,
    "max_rows": 2,                        # Conservative: max 2 rows to propagate
    "require_same_table": True,
    "require_same_section": True,
    "require_coordinate_evidence": False,  # Conservative: no coordinate evidence required
}

# Temperature-only condition keys - should NOT be used as shared condition source
# because they are already handled by Phase 2A/2B (from section/page headings)
TEMPERATURE_KEYS = {"TC", "TJ", "T"}

# Meaningful test condition keys - these indicate real test conditions
TEST_CONDITION_KEYS = {
    "VGS", "VDS", "VDD", "VCC", "V",      # Voltage conditions
    "ID", "IF", "IG", "IC", "IE", "IA",    # Current conditions
    "VR", "VF", "VRRM", "VRWM", "VRSM",   # Reverse voltage
    "RG", "RGATE", "RGS",                    # Gate resistance
    "LOAD", "L", "LS",                      # Load inductance
    "F", "FREQ", "FREQUENCY",               # Frequency
    "VAC", "VDC", "VIN", "VOUT",            # AC/DC voltage
    "TC", "TJ", "T",                        # Temperature (but see note below)
    "PW", "PULSE", " duty",                  # Pulse width / duty cycle
    "SR", "SLEW",                           # Slew rate
}

# Note: TC/TJ/T are temperature keys but they should NOT be used as shared
# condition sources because they are already handled by Phase 2A/2B.
# We only look for keys that indicate TEST CONDITIONS (VGS, IF, VR, etc.)


# ─────────────────────────────────────────────────────────────────────────────
# Diagnostic dataclasses
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PropagationRecord:
    """Record of one condition propagation."""
    group_id: str
    source_row_id: str
    target_row_id: str
    raw_condition: str
    normalized_condition: dict[str, str]
    distance: int
    rule: str
    coordinate_evidence: bool = False


@dataclass
class PropagationResult:
    """Result of shared condition propagation."""
    propagated_count: int = 0
    groups_detected: int = 0
    ambiguous_groups: int = 0
    conflicts: int = 0
    records: list[PropagationRecord] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Condition parsing
# ─────────────────────────────────────────────────────────────────────────────

def _parse_condition(condition_str: str) -> dict[str, str]:
    """
    Parse a condition string into key-value pairs.

    Examples:
    "VGS=-5/+18V; IF=150A; VR=800V" -> {"VGS": "-5/+18V", "IF": "150A", "VR": "800V"}
    "TC=25°C" -> {"TC": "25°C"}
    "RG(ext)=5Ω" -> {"RG(ext)": "5Ω"}
    """
    if not condition_str or not condition_str.strip():
        return {}

    result = {}
    # Split on semicolon
    parts = condition_str.split(";")
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # Match key=value pattern
        # Key can contain letters, digits, +, -, /, (, ), ., _, and space
        # Value is everything after the = sign up to the next semicolon
        m = re.match(r"^([^=]+?)\s*=\s*(.+)$", part)
        if m:
            key = m.group(1).strip()
            value = m.group(2).strip()
            if key and value:
                result[key] = value
    return result


def _has_meaningful_test_conditions(condition_str: str) -> bool:
    """
    Check if a condition string has meaningful test conditions (not just temperature).

    Returns True if the condition has at least one key from TEST_CONDITION_KEYS
    that is NOT a pure temperature key.
    """
    parsed = _parse_condition(condition_str)
    if not parsed:
        return False

    for key in parsed:
        # Check if this is a temperature-only key
        if key.upper() in TEMPERATURE_KEYS:
            continue
        # Check if it's a meaningful test condition
        if key.upper() in TEST_CONDITION_KEYS:
            return True
        # Also accept any key that looks like a test condition (starts with V, I, R, L, F, etc.)
        if key.upper()[:2] in {"VG", "VD", "VV", "ID", "IF", "IG", "VR", "VF", "RG", "LO", "FR"}:
            return True

    return False


def _has_test_conditions(condition_str: str) -> bool:
    """
    Check if a condition string has test conditions (not just temperature).

    Returns True if the condition has at least one key that is NOT a temperature key.
    Used to determine if Phase 2B set temperature-only or with test conditions.
    """
    parsed = _parse_condition(condition_str)
    if not parsed:
        return False
    for key in parsed:
        if key.upper() not in TEMPERATURE_KEYS:
            return True
    return False


def _get_temperature_conditions(condition_str: str) -> dict[str, str]:
    """Extract only temperature conditions (TC, TJ, T) from a condition string."""
    parsed = _parse_condition(condition_str)
    return {k: v for k, v in parsed.items() if k.upper() in TEMPERATURE_KEYS}


# ─────────────────────────────────────────────────────────────────────────────
# Shared condition propagation
# ─────────────────────────────────────────────────────────────────────────────

def propagate_shared_conditions(
    enriched: EnrichedPayload,
    config: dict | None = None,
) -> PropagationResult:
    """
    Propagate shared test conditions to contiguous PARAMETER rows.

    Conservative rules:
    1. Only within the same table
    2. Only within the same section (or both without section_title)
    3. Only contiguous PARAMETER rows
    4. Source must have meaningful test conditions (not just TC/TJ)
    5. Target must have empty raw_condition
    6. Max propagation distance <= max_rows
    7. Stops at any non-PARAMETER row

    Returns a PropagationResult with diagnostic information.
    """
    if config is None:
        config = DEFAULT_CONFIG
    else:
        config = {**DEFAULT_CONFIG, **config}

    if not config.get("enabled", True):
        return PropagationResult()

    max_rows = config.get("max_rows", 2)
    result = PropagationResult()

    group_counter = 0

    for ep in enriched.pages:
        for et in ep.tables:
            # Process each table independently
            table = et
            rows = table.rows

            # Find contiguous PARAMETER rows
            i = 0
            while i < len(rows):
                row = rows[i]

                if row.row_type != RowType.PARAMETER:
                    i += 1
                    continue

                # This is a PARAMETER row
                # Check if it has a non-empty raw_condition with meaningful test conditions
                # BUT: Skip rows that only have VGS and/or IF without other test conditions.
                # These are not true test condition sources (e.g., VFSD has VGS=0V; IF=150A).
                # Real test condition sources have VR, RG, Load, or other specific conditions.
                if row.raw_condition and _has_meaningful_test_conditions(row.raw_condition):
                    # Additional check: skip rows that only have VGS and/or IF
                    parsed = _parse_condition(row.raw_condition)
                    test_keys = set(k.upper() for k in parsed.keys())
                    non_vgs_if_keys = test_keys - {"VGS", "IF"}
                    if not non_vgs_if_keys:
                        # Row only has VGS and/or IF - not a true test condition source
                        i += 1
                        continue

                    # This is a SOURCE row (has real test conditions beyond VGS/IF)
                    # Find contiguous subsequent PARAMETER rows with empty condition
                    source_row = row
                    source_condition = source_row.raw_condition
                    source_parsed = _parse_condition(source_condition)

                    group_counter += 1
                    group_id = f"p{ep.page_number}_t{et.table_index}_group_{group_counter}"

                    propagation_distance = 0
                    j = i + 1

                    while j < len(rows) and propagation_distance < max_rows:
                        target_row = rows[j]

                        # Check boundary conditions
                        if target_row.row_type != RowType.PARAMETER:
                            # Hit a non-PARAMETER row - stop propagation
                            break

                        # Check if target has empty raw_condition
                        if target_row.raw_condition and target_row.raw_condition.strip():
                            # Target has a non-empty condition - stop propagation
                            break

                        # Check if source and target are in the same section
                        if config.get("require_same_section", True):
                            # Both should have the same section_title (or both be None)
                            if source_row.section_title != target_row.section_title:
                                # Different sections - stop
                                break

                        # Check that target doesn't already have a section_title
                        # (meaning it has its own section context)
                        if target_row.section_title is not None and target_row.section_title != source_row.section_title:
                            break

                        # Check that this isn't the Module Physical Characteristics section
                        # by checking if any row in between has a different section
                        # Actually, the section_title check above handles this

                        # This target qualifies for propagation
                        propagation_distance += 1

                        # Apply to target row
                        target_row.shared_condition_group_id = group_id
                        target_row.shared_condition_source_row_id = source_row.row_id

                        # Update condition_sources to include shared_group
                        if target_row.condition_sources is None:
                            target_row.condition_sources = {}
                        target_row.condition_sources["shared_group"] = source_row.row_id

                        # Update quality flags
                        if "shared_condition_propagated" not in target_row.quality_flags:
                            target_row.quality_flags.append("shared_condition_propagated")

                        # Build resolved_condition from source test conditions + Phase 2B temperature
                        # Phase 3A adds test conditions to targets. But:
                        # - If resolved_condition is None: add test conditions (normal case)
                        # - If resolved_condition has test conditions (Phase 2A): don't add (keep Phase 2A)
                        # - If resolved_condition has ONLY temperature (Phase 2B): add test conditions
                        # The last case is when Phase 2B set temperature but no test conditions.
                        should_overwrite = (
                            target_row.resolved_condition is None or
                            (
                                "page_heading_applied" in target_row.quality_flags and
                                not _has_test_conditions(target_row.resolved_condition or "")
                            )
                        )

                        if should_overwrite:
                            merged = dict(source_parsed)

                            # Add temperature from Phase 2B (page heading)
                            if target_row.default_conditions:
                                for k, v in target_row.default_conditions.items():
                                    if k.upper() in TEMPERATURE_KEYS:
                                        if k not in merged:
                                            merged[k] = v

                            # Build resolved_condition string
                            resolved_parts = [f"{k}={v}" for k, v in merged.items()]
                            target_row.resolved_condition = "; ".join(sorted(resolved_parts))

                        # Update context_status
                        if target_row.context_status == ContextStatus.UNCHANGED:
                            target_row.context_status = ContextStatus.RESOLVED

                        # Record propagation
                        record = PropagationRecord(
                            group_id=group_id,
                            source_row_id=source_row.row_id,
                            target_row_id=target_row.row_id,
                            raw_condition=source_condition,
                            normalized_condition=dict(source_parsed),
                            distance=propagation_distance,
                            rule="same_table_same_section_contiguous_parameters",
                            coordinate_evidence=False,
                        )
                        result.records.append(record)
                        result.propagated_count += 1

                        j += 1

                    if propagation_distance > 0:
                        result.groups_detected += 1

                    # Phase 3A: Handle source row if Phase 2B set temperature-only.
                    # This runs even when propagation_distance=0 (standalone source rows like tRR).
                    phase2b_set_temperature = (
                        "page_heading_applied" in source_row.quality_flags
                    )

                    if phase2b_set_temperature:
                        # Phase 2B set temperature (TJ=25°C), add test conditions from source
                        # BUT: skip if source already has meaningful conditions from Phase 2A.
                        # Phase 2A sets meaningful conditions (e.g., TC=25°C from section heading).
                        # Phase 3A should NOT add test conditions to rows that already have
                        # Phase 2A conditions.
                        if source_row.resolved_condition and _has_test_conditions(source_row.resolved_condition):
                            # Source already has meaningful conditions from Phase 2A - skip
                            pass
                        else:
                            # Source has temperature-only from Phase 2B - add test conditions
                            merged = {}
                            if source_row.resolved_condition:
                                merged = _parse_condition(source_row.resolved_condition)
                            merged.update(source_parsed)

                            # Add temperature from page heading if available
                            if source_row.default_conditions:
                                for k, v in source_row.default_conditions.items():
                                    if k.upper() in TEMPERATURE_KEYS:
                                        if k not in merged:
                                            merged[k] = v

                            source_row.resolved_condition = "; ".join(
                                sorted(f"{k}={v}" for k, v in merged.items())
                            )

                i += 1

    return result


def apply_propagation_to_source(
    enriched: EnrichedPayload,
    result: PropagationResult,
) -> None:
    """
    Mark the source rows of each propagation group.

    This adds "shared_condition_source" to their quality_flags.
    """
    source_ids = set(r.source_row_id for r in result.records)

    for ep in enriched.pages:
        for et in ep.tables:
            for row in et.rows:
                if row.row_id in source_ids:
                    if "shared_condition_source" not in row.quality_flags:
                        row.quality_flags.append("shared_condition_source")
