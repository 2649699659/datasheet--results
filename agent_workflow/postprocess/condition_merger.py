"""
Condition Monotonic Merge Implementation.

This module implements the monotonic merge rules for conditions:

1. resolved_condition is the base (from Step 0.5)
2. Agent 2 condition cannot整体 replace the base
3. Parse conditions into key/value pairs and merge
4. Agent 2 can add new keys
5. Same key, same value = deduplicate
6. Same key, different value = Agent 2 must have explicit evidence to override
7. Agent 2 condition shorter than resolved cannot delete keys from resolved
8. Unparseable Agent 2 condition = keep resolved, audit original
9. raw_condition is evidence only, not used for override
10. Result must be idempotent
"""

import re
from dataclasses import dataclass, field
from typing import Optional
from .finalizer_models import ConditionSlot


# Condition key patterns for normalization
CONDITION_KEYS = [
    "VDS", "VGS", "VDD", "ID", "IC", "IF", "VDSs", "VCE", "VCES",
    "RG", "RG\\(ext\\)", "Load", "f", "f=", "MHz", "kHz", "VAC", "VDC",
    "TC", "TJ", "TC=?", "TJ=?", "dIF/dt", "dI", "dt",
    "VDS=", "VGS=", "VDD=", "ID=", "IF=", "RG=", "RG\\(ext\\)=",
    "VDSs=", "VCE=", "VCES=", "Load=", "f=", "VAC=", "VDC=",
]

# Regex patterns for parsing condition key=value pairs
CONDITION_PATTERN = re.compile(
    r'([A-Za-z_]+(?:\[(?:ext|on|off)\])?(?:\([A-Za-z_]+\))?)'  # key
    r'\s*'  
    r'='
    r'\s*'
    r'([^;,\n]+?)'  # value
    r'(?:;|,|\n|$)'
)


def parse_condition(condition: str) -> dict[str, str]:
    """
    Parse a condition string into a dictionary of key=value pairs.
    
    Examples:
        "VDS=800V; VGS=-5/+18V; ID=150A" -> {"VDS": "800V", "VGS": "-5/+18V", "ID": "150A"}
        "TC=25°C" -> {"TC": "25°C"}
    """
    if not condition:
        return {}
    
    result = {}
    
    # Try the regex pattern
    for match in CONDITION_PATTERN.finditer(condition):
        key = match.group(1).strip()
        value = match.group(2).strip()
        
        # Normalize key
        key = normalize_condition_key(key)
        if key:
            result[key] = value
    
    # Fallback: try simple splitting by semicolons
    if not result:
        for part in condition.split(";"):
            part = part.strip()
            if "=" in part:
                key, value = part.split("=", 1)
                key = normalize_condition_key(key.strip())
                if key:
                    result[key] = value.strip()
    
    return result


def normalize_condition_key(key: str) -> str:
    """
    Normalize a condition key to a canonical form.
    
    Examples:
        "TC" -> "TC"
        "TJ" -> "TJ"
        "RG(ext)" -> "RG"
        "VDSs" -> "VDS"
        "VDS(sus)" -> "VDS"
    """
    key = key.strip()
    
    # Remove (ext), (on), (off) suffixes
    key = re.sub(r'\((ext|on|off)\)', '', key)
    
    # Normalize common variations
    key_mapping = {
        "VDSs": "VDS",
        "VCES": "VCE",
        "VDS(sus)": "VDS",
    }
    
    return key_mapping.get(key, key)


def format_condition(parsed: dict[str, str]) -> str:
    """
    Format a parsed condition dictionary back into a condition string.
    """
    if not parsed:
        return ""
    
    parts = []
    for key in sorted(parsed.keys()):
        value = parsed[key]
        parts.append(f"{key}={value}")
    
    return "; ".join(parts)


@dataclass
class ConditionMergeResult:
    """Result of merging conditions."""
    merged_condition: str
    merged_parsed: dict[str, str]
    condition_slots: list[ConditionSlot]
    conflicts: list[dict]  # List of conflict descriptions
    audits: list[str]  # Audit notes
    deleted_keys: list[str]  # Keys that would have been deleted (flagged)


class ConditionMerger:
    """
    Implements monotonic condition merge with full audit trail.
    """
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.conflicts = []
        self.audits = []
        self.deleted_keys = []
    
    def merge(
        self,
        resolved_condition: str | None,
        agent2_condition: str | None,
        agent2_has_explicit_evidence: bool = False,
        agent2_row_id: str | None = None,
    ) -> ConditionMergeResult:
        """
        Merge resolved_condition and agent2_condition according to monotonic rules.
        
        Args:
            resolved_condition: Condition from Step 0.5 (the base)
            agent2_condition: Condition from Agent 2
            agent2_has_explicit_evidence: Whether Agent 2 has explicit row evidence
            agent2_row_id: The row_id where Agent 2 found the condition
            
        Returns:
            ConditionMergeResult with merged condition and audit trail
        """
        self.reset()
        
        # Parse conditions
        resolved_parsed = parse_condition(resolved_condition) if resolved_condition else {}
        agent2_parsed = parse_condition(agent2_condition) if agent2_condition else {}
        
        # Start with resolved as base
        merged_parsed = dict(resolved_parsed)
        condition_slots = []
        
        # Add resolved conditions as slots
        for key, value in resolved_parsed.items():
            condition_slots.append(ConditionSlot(
                key=key,
                value=value,
                source="resolved",
            ))
        
        # Process Agent 2 conditions
        for key, value in agent2_parsed.items():
            if key in merged_parsed:
                # Key exists in resolved
                if merged_parsed[key] == value:
                    # Same value = deduplicate (already added as resolved)
                    pass
                else:
                    # Different value = conflict
                    if agent2_has_explicit_evidence and agent2_row_id:
                        # Agent 2 has explicit evidence, allow override
                        merged_parsed[key] = value
                        # Update the slot source
                        for slot in condition_slots:
                            if slot.key == key:
                                slot.source = "agent2"
                                slot.evidence = f"row:{agent2_row_id}"
                                break
                        self.audits.append(f"Agent 2 overrode {key}={resolved_parsed[key]} -> {value} (explicit evidence)")
                    else:
                        # No explicit evidence, keep resolved and record conflict
                        self.conflicts.append({
                            "key": key,
                            "resolved_value": resolved_parsed[key],
                            "agent2_value": value,
                            "resolution": "kept_resolved",
                            "agent2_row_id": agent2_row_id,
                        })
                        self.audits.append(f"Conflict: {key}={resolved_parsed[key]} vs {value}, kept resolved (no explicit evidence)")
            else:
                # New key from Agent 2, can be added
                merged_parsed[key] = value
                condition_slots.append(ConditionSlot(
                    key=key,
                    value=value,
                    source="agent2",
                    evidence=f"row:{agent2_row_id}" if agent2_row_id else "",
                ))
        
        # Rule 7: Check if Agent 2 condition is shorter and would delete keys
        if agent2_condition and resolved_condition:
            agent2_keys = set(agent2_parsed.keys())
            resolved_keys = set(resolved_parsed.keys())
            
            # If Agent 2 condition has fewer keys, check for deletion
            if len(agent2_keys) < len(resolved_keys):
                deleted = resolved_keys - agent2_keys
                if deleted:
                    # Agent 2 shorter condition would delete keys - this is a problem
                    for key in deleted:
                        # Agent 2 condition is shorter, don't delete resolved keys
                        self.conflicts.append({
                            "key": key,
                            "resolved_value": resolved_parsed[key],
                            "agent2_value": None,
                            "resolution": "kept_resolved",
                            "issue": "agent2_shorter_would_delete",
                        })
                        self.deleted_keys.append(key)
                    self.audits.append(f"Agent 2 condition shorter, flagged potential deletion of: {deleted}")
        
        # Rule 8: If Agent 2 condition is unparseable, keep resolved
        if agent2_condition and not agent2_parsed and resolved_parsed:
            self.audits.append(f"Agent 2 condition unparseable: '{agent2_condition}', kept resolved")
        
        return ConditionMergeResult(
            merged_condition=format_condition(merged_parsed),
            merged_parsed=merged_parsed,
            condition_slots=condition_slots,
            conflicts=self.conflicts,
            audits=self.audits,
            deleted_keys=self.deleted_keys,
        )


def merge_final_conditions(
    resolved_condition: str | None,
    agent2_condition: str | None,
    agent2_has_explicit_evidence: bool = False,
    agent2_row_id: str | None = None,
) -> ConditionMergeResult:
    """
    Convenience function for merging conditions.
    """
    merger = ConditionMerger()
    return merger.merge(
        resolved_condition=resolved_condition,
        agent2_condition=agent2_condition,
        agent2_has_explicit_evidence=agent2_has_explicit_evidence,
        agent2_row_id=agent2_row_id,
    )
