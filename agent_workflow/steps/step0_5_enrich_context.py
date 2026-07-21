"""
step0_5_enrich_context.py — Step 0.5: Enrich Context

Pure Python enrichment layer between Step 0 and Step 1.
Converts CamelotPayload → EnrichedPayload with row-level classification.

Phase 1: Row-level classification (empty/separator/column_header/section_title/table_title/parameter/unknown)
Phase 2A: Table/section title tracking and temperature condition resolution

This step does NOT:
- Call any LLM
- Modify CamelotPayload
- Delete/add/merge rows
- Use target_fields.yaml
- Perform shared condition propagation (Phase 2A handles heading-level conditions only)

Input:  CamelotPayload (from Step 0)
Output: EnrichedPayload (to Step 1)
"""

import logging
from pathlib import Path

from ..contracts import CamelotPayload
from ..artifacts import ArtifactPaths, load_payload, save_enriched_payload, save_step0_5_report
from ..enrichment import EnrichedPayload, enrich_payload

logger = logging.getLogger(__name__)


def run(payload: CamelotPayload, artifact_paths: ArtifactPaths) -> EnrichedPayload:
    """
    Enrich a CamelotPayload with row-level classification.

    Args:
        payload: CamelotPayload from Step 0.
        artifact_paths: Artifact paths manager.

    Returns:
        EnrichedPayload with enriched rows.
    """
    logger.info("Step 0.5: Enriching context from CamelotPayload")

    # Perform enrichment (Phase 1, 2A, 2B, 3A)
    # pdf_path is required for Phase 2B (page-level heading resolution)
    enriched = enrich_payload(payload, pdf_path=payload.pdf_path)

    logger.info(
        f"Step 0.5: Enriched {enriched.enriched_row_count} rows "
        f"(types: {enriched.row_type_counts})"
    )

    # Build and save enrichment report
    report = build_enrichment_report(enriched)
    save_step0_5_report(report, artifact_paths.step0_5_report())
    logger.info(f"Step 0.5: Saved report to {artifact_paths.step0_5_report()}")

    # Save artifact
    save_enriched_payload(enriched, artifact_paths.step0_5_enriched_payload())
    logger.info(f"Step 0.5: Saved to {artifact_paths.step0_5_enriched_payload()}")

    return enriched


def build_enrichment_report(enriched: EnrichedPayload) -> dict:
    """
    Build the Step 0.5 enrichment report from an EnrichedPayload.

    Returns a dict with the following structure:
    {
        "status": "success | failed | disabled",
        "tables_processed": int,
        "rows_processed": int,
        "row_type_counts": dict,
        "heading_conditions_applied": int,
        "page_headings_applied": int,
        "shared_conditions_propagated": int,
        "manufacturer_status": str,
        "manufacturer_canonical_value": str | None,
        "manufacturer_evidence_count": int,
        "ambiguous_rows": list[str],
        "conflicts": list,
        "warnings": list[str],
        "cache_stats": dict,
    }
    """
    # Count page_heading_applied rows
    page_headings_applied = 0
    for page in enriched.pages:
        for table in page.tables:
            for row in table.rows:
                if "page_heading_applied" in row.quality_flags:
                    page_headings_applied += 1

    # Extract manufacturer info
    manufacturer_status = ""
    manufacturer_canonical_value = None
    manufacturer_evidence_count = 0
    doc_meta = enriched.document_metadata or {}
    mfr = doc_meta.get("manufacturer", {})
    if mfr:
        manufacturer_status = mfr.get("status", "")
        manufacturer_canonical_value = mfr.get("canonical_value")
        manufacturer_evidence_count = len(mfr.get("candidates", []))

    return {
        "status": "success",
        "tables_processed": sum(len(p.tables) for p in enriched.pages),
        "rows_processed": enriched.enriched_row_count,
        "row_type_counts": enriched.row_type_counts,
        "heading_conditions_applied": enriched.heading_conditions_applied,
        "page_headings_applied": page_headings_applied,
        "shared_conditions_propagated": enriched.shared_conditions_propagated,
        "manufacturer_status": manufacturer_status,
        "manufacturer_canonical_value": manufacturer_canonical_value,
        "manufacturer_evidence_count": manufacturer_evidence_count,
        "ambiguous_rows": enriched.ambiguous_title_rows,
        "conflicts": [],  # TODO: track conflicts in Phase 3A if needed
        "warnings": [],
        "cache_stats": {},
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI (for testing)
# ─────────────────────────────────────────────────────────────────────────────

def _load_payload_from_json(path: Path) -> CamelotPayload:
    """Load CamelotPayload from JSON file."""
    with open(path, encoding="utf-8") as f:
        import json
        d = json.load(f)
    from ..contracts import CamelotPayload
    return CamelotPayload.from_dict(d)


if __name__ == "__main__":
    import sys
    from pathlib import Path

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    if len(sys.argv) < 3:
        print("Usage: python3 step0_5_enrich_context.py <camelot_payload.json> <output_dir>")
        sys.exit(1)

    camelot_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    pdf_stem = camelot_path.stem.replace("_camelot_payload", "").replace("step0_", "")

    ap = ArtifactPaths(output_dir, pdf_stem)
    ap.ensure_dirs()

    # Load CamelotPayload
    payload = _load_payload_from_json(camelot_path)

    # Enrich
    enriched = run(payload, ap)

    print(f"\nEnrichment summary:")
    print(f"  Total rows: {enriched.enriched_row_count}")
    for rt, count in sorted(enriched.row_type_counts.items()):
        print(f"  {rt}: {count}")
