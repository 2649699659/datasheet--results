"""
step0_6_parameter_inventory.py — Step 0.6: Parameter Inventory.

Phase 5: Extract all parameter rows from PDF, not just predefined target fields.

This step runs in parallel with Agent 1/2/3 and does not depend on LLM output.
"""

import json
from pathlib import Path

from ..enrichment.models import EnrichedPayload
from ..enrichment.materialize_parameter_inventory import (
    materialize_parameter_inventory,
    ParameterRecord,
    InventoryReport,
)
from ..enrichment.parameter_inventory_models import MappingStatus
from ..artifacts import ArtifactPaths, save_parameter_inventory, load_parameter_inventory


def run(
    enriched_payload: EnrichedPayload,
    artifact_paths: ArtifactPaths,
    canonical_results: list[dict] | None = None,
) -> tuple[list[ParameterRecord], InventoryReport]:
    """
    Generate Parameter Inventory from EnrichedPayload.

    Args:
        enriched_payload: Step 0.5 enriched payload
        artifact_paths: Artifact paths for saving outputs
        canonical_results: Optional list of canonical field results for mapping

    Returns:
        Tuple of (list of ParameterRecord, InventoryReport)
    """
    # Generate inventory
    records, report = materialize_parameter_inventory(enriched_payload)

    # Apply canonical mapping if available
    if canonical_results:
        records = _apply_canonical_mapping(records, canonical_results)

    # Save artifacts
    save_parameter_inventory(
        records,
        artifact_paths.output_dir / artifact_paths.step0_6_parameter_inventory(),
    )

    # Generate and save report
    report_data = report.to_dict()
    report_path = artifact_paths.output_dir / artifact_paths.step0_6_inventory_report()
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    return records, report


def _apply_canonical_mapping(
    records: list[ParameterRecord],
    canonical_results: list[dict],
) -> list[ParameterRecord]:
    """
    Apply canonical field mapping to inventory records.

    Uses source_row_id to match records with canonical results.
    """
    # Build lookup from source_row_id to canonical field_id
    row_id_to_field: dict[str, str] = {}
    for result in canonical_results:
        source_row_id = result.get("source_row_id")
        field_id = result.get("field_id")
        if source_row_id and field_id:
            row_id_to_field[source_row_id] = field_id

    # Apply mapping
    for record in records:
        if record.row_id in row_id_to_field:
            record.canonical_field_id = row_id_to_field[record.row_id]
            record.mapping_status = MappingStatus.MAPPED
            record.source_row_id = record.row_id

    return records


def load_inventory(artifact_paths: ArtifactPaths) -> list[ParameterRecord]:
    """Load Parameter Inventory from artifact."""
    inventory_path = artifact_paths.output_dir / artifact_paths.step0_6_parameter_inventory()
    return load_parameter_inventory(inventory_path)


def load_inventory_report(artifact_paths: ArtifactPaths) -> dict:
    """Load Inventory Report from artifact."""
    report_path = artifact_paths.output_dir / artifact_paths.step0_6_inventory_report()
    if not report_path.exists():
        return {}
    with open(report_path, "r", encoding="utf-8") as f:
        return json.load(f)
