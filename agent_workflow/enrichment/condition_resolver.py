"""
condition_resolver.py — Unified condition resolution for enriched rows.

This module provides the single source of truth for resolving conditions
from multiple layers (raw, shared_group, table_default, page_default).

Priority (later layers override earlier layers for SAME key):
    page_default → table_default → shared_group → raw

Different keys are ALWAYS preserved.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConditionLayer:
    """
    A single condition layer with parsed key-value pairs and metadata.
    """
    values: dict[str, str] = field(default_factory=dict)
    source_row_ids: list[str] = field(default_factory=list)
    evidence_type: str | None = None  # e.g., "raw_row_condition", "table_heading", "page_heading", "shared_group"
    source_texts: list[str] = field(default_factory=list)  # Original text snippets


@dataclass
class RowConditionContext:
    """
    Container for all condition layers for a single row.
    
    Layers are isolated - each phase writes to its own layer.
    The resolver merges them into final resolved_condition.
    """
    raw: ConditionLayer = field(default_factory=ConditionLayer)
    shared_group: ConditionLayer = field(default_factory=ConditionLayer)
    table_default: ConditionLayer = field(default_factory=ConditionLayer)
    page_default: ConditionLayer = field(default_factory=ConditionLayer)
    conflicts: list[dict] = field(default_factory=list)  # List of conflict records


@dataclass
class ConditionResolutionResult:
    """
    Result of resolving a row's condition context.
    """
    # Merged key-value pairs
    values: dict[str, str]
    # Rendered condition string (e.g., "VDS=800V; TC=25°C; TJ=25°C")
    rendered_text: str
    # Condition sources (derived from layers)
    sources: dict[str, Any]
    # Conflicts detected during merge
    conflicts: list[dict]
    # Which layers contributed to the final result
    layer_contributions: dict[str, bool]  # layer_name -> was_used


# Temperature keys that should not conflict with each other
TEMPERATURE_KEYS = {"TC", "TJ", "T", "TA", "TS"}


def resolve_condition_context(context: RowConditionContext) -> ConditionResolutionResult:
    """
    Resolve a row's condition context into a final resolved_condition.
    
    Priority (same key conflict resolution):
        raw > shared_group > table_default > page_default
    
    Different keys are ALWAYS preserved.
    
    Example:
        page_default:  {"TJ": "25°C"}
        table_default: {"TC": "25°C"}
        shared_group:  {"VDS": "800V", "ID": "150A"}
        raw:           {"VGS": "0V"}
        
        Result: {"TJ": "25°C", "TC": "25°C", "VDS": "800V", "ID": "150A", "VGS": "0V"}
    """
    # Track which layers contributed
    layer_contributions = {
        "page_default": False,
        "table_default": False,
        "shared_group": False,
        "raw": False,
    }
    
    # Start with lowest priority, build up
    # Merge order: page_default → table_default → shared_group → raw
    # Later layers override earlier for SAME key
    
    merged: dict[str, str] = {}
    conflicts: list[dict] = []
    
    layer_order = [
        ("page_default", context.page_default),
        ("table_default", context.table_default),
        ("shared_group", context.shared_group),
        ("raw", context.raw),
    ]
    
    for layer_name, layer in layer_order:
        if layer.values:
            layer_contributions[layer_name] = True
            
            for key, value in layer.values.items():
                # Check for conflict (same key, different value)
                if key in merged and merged[key] != value:
                    conflict = {
                        "key": key,
                        "lower_layer": _get_lower_layer_name(layer_name, layer_order),
                        "lower_value": merged[key],
                        "higher_layer": layer_name,
                        "higher_value": value,
                        "winner": layer_name,  # Higher layer wins
                        "winner_value": value,
                    }
                    conflicts.append(conflict)
                    # Higher layer overrides lower layer
                    merged[key] = value
                else:
                    merged[key] = value
    
    # Render the merged conditions
    # Keep consistent order: non-temperature keys first, then temperature keys
    non_temp = {k: v for k, v in merged.items() if k.upper() not in TEMPERATURE_KEYS}
    temp = {k: v for k, v in merged.items() if k.upper() in TEMPERATURE_KEYS}
    
    # Sort each group by key name
    parts = []
    for k in sorted(non_temp.keys()):
        parts.append(f"{k}={non_temp[k]}")
    for k in sorted(temp.keys()):  # Temperature last
        parts.append(f"{k}={temp[k]}")
    
    rendered_text = "; ".join(parts) if parts else ""
    
    # Build sources dict from layers
    sources = _build_sources_dict(context, layer_contributions)
    
    return ConditionResolutionResult(
        values=merged,
        rendered_text=rendered_text,
        sources=sources,
        conflicts=conflicts,
        layer_contributions=layer_contributions,
    )


def _get_lower_layer_name(current_layer: str, layer_order: list[tuple]) -> str:
    """Get the name of the lower-priority layer that was overridden."""
    layer_names = [name for name, _ in layer_order]
    current_idx = layer_names.index(current_layer)
    if current_idx > 0:
        return layer_names[current_idx - 1]
    return current_layer


def _build_sources_dict(context: RowConditionContext, contributions: dict[str, bool]) -> dict[str, Any]:
    """
    Build condition_sources dict from layers.
    
    For backward compatibility, also includes the old keys:
    - 'row': derived from 'raw' layer
    - 'table_heading': derived from 'table_default' layer
    - 'page_heading': derived from 'page_default' layer
    """
    sources = {}
    
    if contributions.get("raw"):
        sources["raw"] = {
            "values": dict(context.raw.values),
            "source_row_ids": list(context.raw.source_row_ids),
            "evidence_type": context.raw.evidence_type,
        }
        # Backward compatibility: 'row' key
        if context.raw.values:
            sources["row"] = str(dict(context.raw.values))
        else:
            sources["row"] = None
    
    if contributions.get("shared_group"):
        sources["shared_group"] = {
            "values": dict(context.shared_group.values),
            "source_row_ids": list(context.shared_group.source_row_ids),
            "evidence_type": context.shared_group.evidence_type,
        }
    
    if contributions.get("table_default"):
        sources["table_default"] = {
            "values": dict(context.table_default.values),
            "source_row_ids": list(context.table_default.source_row_ids),
            "evidence_type": context.table_default.evidence_type,
        }
        # Backward compatibility: 'table_heading' key
        if context.table_default.values:
            sources["table_heading"] = str(dict(context.table_default.values))
        else:
            sources["table_heading"] = None
    
    if contributions.get("page_default"):
        sources["page_default"] = {
            "values": dict(context.page_default.values),
            "source_row_ids": list(context.page_default.source_row_ids),
            "evidence_type": context.page_default.evidence_type,
        }
        # Backward compatibility: 'page_heading' key
        if context.page_default.values:
            sources["page_heading"] = str(dict(context.page_default.values))
        else:
            sources["page_heading"] = None
    
    # If no contributions, ensure backward compatibility keys exist
    if not contributions.get("raw"):
        sources.setdefault("row", None)
    if not contributions.get("table_default"):
        sources.setdefault("table_heading", None)
    if not contributions.get("page_default"):
        sources.setdefault("page_heading", None)
    
    return sources


def condition_context_to_dict(ctx: RowConditionContext | None) -> dict | None:
    """Serialize RowConditionContext to dict for JSON storage."""
    if ctx is None:
        return None
    return {
        "raw": {
            "values": ctx.raw.values,
            "source_row_ids": ctx.raw.source_row_ids,
            "evidence_type": ctx.raw.evidence_type,
            "source_texts": ctx.raw.source_texts,
        },
        "shared_group": {
            "values": ctx.shared_group.values,
            "source_row_ids": ctx.shared_group.source_row_ids,
            "evidence_type": ctx.shared_group.evidence_type,
            "source_texts": ctx.shared_group.source_texts,
        },
        "table_default": {
            "values": ctx.table_default.values,
            "source_row_ids": ctx.table_default.source_row_ids,
            "evidence_type": ctx.table_default.evidence_type,
            "source_texts": ctx.table_default.source_texts,
        },
        "page_default": {
            "values": ctx.page_default.values,
            "source_row_ids": ctx.page_default.source_row_ids,
            "evidence_type": ctx.page_default.evidence_type,
            "source_texts": ctx.page_default.source_texts,
        },
        "conflicts": ctx.conflicts,
    }


def dict_to_condition_context(d: dict) -> RowConditionContext:
    """Deserialize RowConditionContext from dict (with backward compatibility)."""
    if d is None:
        return RowConditionContext()
    
    raw_data = d.get("raw", {})
    shared_data = d.get("shared_group", {})
    table_data = d.get("table_default", {})
    page_data = d.get("page_default", {})
    
    return RowConditionContext(
        raw=ConditionLayer(
            values=dict(raw_data.get("values", {})),
            source_row_ids=list(raw_data.get("source_row_ids", [])),
            evidence_type=raw_data.get("evidence_type"),
            source_texts=list(raw_data.get("source_texts", [])),
        ),
        shared_group=ConditionLayer(
            values=dict(shared_data.get("values", {})),
            source_row_ids=list(shared_data.get("source_row_ids", [])),
            evidence_type=shared_data.get("evidence_type"),
            source_texts=list(shared_data.get("source_texts", [])),
        ),
        table_default=ConditionLayer(
            values=dict(table_data.get("values", {})),
            source_row_ids=list(table_data.get("source_row_ids", [])),
            evidence_type=table_data.get("evidence_type"),
            source_texts=list(table_data.get("source_texts", [])),
        ),
        page_default=ConditionLayer(
            values=dict(page_data.get("values", {})),
            source_row_ids=list(page_data.get("source_row_ids", [])),
            evidence_type=page_data.get("evidence_type"),
            source_texts=list(page_data.get("source_texts", [])),
        ),
        conflicts=list(d.get("conflicts", [])),
    )


def apply_resolved_condition_to_row(row: Any, result: ConditionResolutionResult) -> None:
    """
    Apply resolution result to an EnrichedRow.
    
    This sets:
    - row.resolved_condition
    - row.condition_sources
    - row.condition_context.conflicts
    """
    row.resolved_condition = result.rendered_text
    row.condition_sources = result.sources
    
    # Update conflicts in context
    if hasattr(row, 'condition_context') and row.condition_context:
        row.condition_context.conflicts = result.conflicts


def _parse_condition_str(condition_str: str) -> dict[str, str]:
    """
    Parse a condition string into key-value pairs.
    
    Example: "VDS=800V; VGS=-5/+18V; ID=150A"
    Returns: {"VDS": "800V", "VGS": "-5/+18V", "ID": "150A"}
    
    Handles:
    - Semicolon and comma separators
    - Keys with parentheses like RG(ext)
    - Special characters like Ω, µ, ±
    """
    import re
    
    if not condition_str:
        return {}
    
    # Split by semicolon or comma followed by space
    parts = re.split(r'[;,](?=\s*[A-Z])', condition_str)
    
    result = {}
    for part in parts:
        part = part.strip()
        if not part:
            continue
        
        # Match key=value pattern
        # Key can contain parentheses, letters, numbers, underscore
        # Value is everything after the =
        match = re.match(r'^([A-Za-z_][A-Za-z0-9_()]*)\s*=\s*(.+)$', part)
        if match:
            key = match.group(1).strip()
            value = match.group(2).strip()
            # Remove trailing period or semicolon
            value = re.sub(r'[.;]$', '', value).strip()
            if key and value:
                result[key] = value
    
    return result
