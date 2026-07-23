"""
step1_agent_candidate.py — Step 1: Agent 1 — Candidate Row Selection

Reviews CamelotPayload tables and selects candidate rows for each target field.
Uses the Agent 1 LLM prompt for table row classification.

Input:  CamelotPayload (from Step 0)
Output: Agent1Result (candidates per field)
"""

import json
import logging
import time
from pathlib import Path
from typing import Any

from ..contracts import (
    CamelotPayload,
    CamelotPage,
    CamelotTable,
    CandidateRow,
    FieldCandidates,
    Agent1Result,
)
from ..enrichment.models import EnrichedPayload as EnrichedPayloadModel
from ..artifacts import ArtifactPaths, save_agent1, load_payload

logger = logging.getLogger(__name__)

# Load Agent 1 prompt
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "agent1_table_classifier_v1.md"
TARGET_FIELDS_PATH = Path(__file__).parent.parent.parent / "config" / "target_fields.yaml"


def _load_prompt() -> str:
    if PROMPT_PATH.exists():
        return PROMPT_PATH.read_text(encoding="utf-8")
    return ""


def _load_target_fields() -> list[dict]:
    """Load target fields from YAML config."""
    import yaml
    if TARGET_FIELDS_PATH.exists():
        with open(TARGET_FIELDS_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data.get("fields", [])
    return []


def _build_llm_input(
    payload: CamelotPayload,
    target_fields: list[dict],
    enriched_payload: EnrichedPayloadModel | None = None,
) -> str:
    """
    Build the LLM input text from CamelotPayload and target fields.

    When enriched_payload is provided, includes enriched context per row:
    - row_type (PARAMETER, TABLE_TITLE, SECTION_TITLE, etc.)
    - resolved_condition (test condition resolved from heading or shared context)
    - context_status (UNCHANGED, RESOLVED, AMBIGUOUS)
    - quality_flags (page_heading_applied, shared_condition_propagated, etc.)
    """
    lines = []
    lines.append("# INPUT DATA\n")
    lines.append(f"Document: {payload.file_name}\n")

    # Build a lookup from (page_number, table_index, row_index) to enriched row
    enriched_lookup: dict[tuple[int, int, int], object] = {}
    if enriched_payload is not None:
        for page in enriched_payload.pages:
            for table in page.tables:
                for row in table.rows:
                    key = (page.page_number, table.table_index, row.row_index)
                    enriched_lookup[key] = row

    for page in payload.pages:
        for table in page.tables:
            lines.append(f"\n## Page {page.page_number}, Table {table.table_index} (flavor={table.flavor}, score={table.score:.1f})")
            for row in table.rows:
                # Escape cells
                cells = [c.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") for c in row.cells]
                row_line = f"  ROW[{row.row_index}]: {cells}"

                # Add enriched context if available
                if enriched_payload is not None:
                    key = (page.page_number, table.table_index, row.row_index)
                    enriched_row = enriched_lookup.get(key)
                    if enriched_row is not None:
                        # row_type
                        row_type = getattr(enriched_row, 'row_type', None)
                        if row_type:
                            row_line += f"  # type={row_type.value if hasattr(row_type, 'value') else row_type}"
                        # resolved_condition
                        resolved_cond = getattr(enriched_row, 'resolved_condition', None)
                        if resolved_cond:
                            row_line += f", resolved_condition={resolved_cond}"
                        # context_status
                        ctx_status = getattr(enriched_row, 'context_status', None)
                        if ctx_status:
                            row_line += f", context_status={ctx_status.value if hasattr(ctx_status, 'value') else ctx_status}"
                        # quality_flags
                        quality_flags = getattr(enriched_row, 'quality_flags', [])
                        if quality_flags:
                            row_line += f", quality_flags={quality_flags}"

                lines.append(row_line)

    lines.append("\n# TARGET FIELDS\n")
    for f in target_fields:
        lines.append(f"- {f['id']}: {f.get('label', '')} (aliases: {', '.join(f.get('aliases', []))}, target_unit: {f.get('target_unit', '')})")

    lines.append("\n# YOUR TASK\n")
    lines.append("Review each table and identify candidate rows for each target field.")
    lines.append("For each target field, select the BEST candidate row (highest confidence).")
    lines.append("Also list all review candidates (lower confidence but still possible).")
    lines.append("Return STRICT JSON only:\n")

    lines.append("""```json
{
  "candidates": [
    {
      "field_id": "voltage_rating",
      "label": "Drain-Source Voltage",
      "target_unit": "V",
      "selected": { "source_page": 1, "table_index": 0, "row_index": 3, "confidence": 0.95, "match_type": "exact", ... },
      "review": [
        { "source_page": 2, "table_index": 1, "row_index": 5, "confidence": 0.8, ... }
      ]
    }
  ]
}
```""")

    return "\n".join(lines)


def _call_llm(prompt: str, output_path: Path | None = None) -> str:
    """Call LLM with prompt. Reads from output_path if exists (for testing)."""
    import os

    # Check cache
    if output_path and output_path.exists():
        logger.info(f"Reading cached LLM response from {output_path}")
        return output_path.read_text(encoding="utf-8")

    # Try OpenAI-compatible API
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        raise RuntimeError("No API key found in environment (OPENAI_API_KEY or MINIMAX_API_KEY)")

    # Determine endpoint
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.minimaxi.chat/v1")
    endpoint = f"{base_url.rstrip('/')}/chat/completions"

    import urllib.request
    data = {
        "model": os.environ.get("LLM_MODEL", "MiniMax-M2.7"),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "top_p": 1,
        "seed": 42,
    }

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(data).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"]

            # Save response
            if output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(content, encoding="utf-8")

            return content
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise RuntimeError(f"LLM API error {e.code}: {error_body}")


def _parse_llm_output(content: str, payload: CamelotPayload) -> Agent1Result:
    """Parse LLM output into Agent1Result."""
    # Extract JSON from response
    json_str = _extract_json(content)
    d = json.loads(json_str)

    fields_out = []
    total_candidates = 0
    selected_count = 0
    review_count = 0

    for fd in d.get("candidates", []):
        field_id = fd.get("field_id")
        label = fd.get("label", "")
        target_unit = fd.get("target_unit", "")

        selected_d = fd.get("selected") or {}
        review_list = fd.get("review") or []

        # Build selected candidate
        selected = None
        if selected_d:
            page_num = selected_d.get("source_page", 0)
            tbl_idx = selected_d.get("table_index", 0)
            row_idx = selected_d.get("row_index", 0)

            src_page = next((p for p in payload.pages if p.page_number == page_num), None)
            src_table = None
            if src_page:
                src_table = next((t for t in src_page.tables if t.table_index == tbl_idx), None)
            src_row = src_table.rows[row_idx] if src_table and row_idx < len(src_table.rows) else None

            selected = CandidateRow(
                field_id=field_id,
                label=label,
                symbol=selected_d.get("symbol"),
                parameter_name=selected_d.get("parameter_name"),
                candidate_type="selected",
                source_page=page_num,
                table_index=tbl_idx,
                row_index=row_idx,
                row_cells=src_row.cells if src_row else [],
                source_text=selected_d.get("source_text", ""),
                value=selected_d.get("value"),
                min=selected_d.get("min"),
                typ=selected_d.get("typ"),
                max=selected_d.get("max"),
                unit=selected_d.get("unit"),
                original_unit=selected_d.get("original_unit"),
                condition=selected_d.get("condition"),
                confidence=selected_d.get("confidence", 0.0),
                match_type=selected_d.get("match_type", "unknown"),
                warnings=selected_d.get("warnings", []),
                review_reason=selected_d.get("review_reason"),
            )
            selected_count += 1

        # Build review candidates
        review_candidates = []
        for rd in review_list:
            page_num = rd.get("source_page", 0)
            tbl_idx = rd.get("table_index", 0)
            row_idx = rd.get("row_index", 0)

            src_page = next((p for p in payload.pages if p.page_number == page_num), None)
            src_table = src_page.tables[tbl_idx] if src_page and tbl_idx < len(src_page.tables) else None
            src_row = src_table.rows[row_idx] if src_table and row_idx < len(src_table.rows) else None

            review_candidates.append(CandidateRow(
                field_id=field_id,
                label=label,
                symbol=rd.get("symbol"),
                parameter_name=rd.get("parameter_name"),
                candidate_type="review",
                source_page=page_num,
                table_index=tbl_idx,
                row_index=row_idx,
                row_cells=src_row.cells if src_row else [],
                source_text=rd.get("source_text", ""),
                value=rd.get("value"),
                min=rd.get("min"),
                typ=rd.get("typ"),
                max=rd.get("max"),
                unit=rd.get("unit"),
                original_unit=rd.get("original_unit"),
                condition=rd.get("condition"),
                confidence=rd.get("confidence", 0.0),
                match_type=rd.get("match_type", "unknown"),
                warnings=rd.get("warnings", []),
                review_reason=rd.get("review_reason"),
            ))
            review_count += 1

        candidates = ([selected] if selected else []) + review_candidates
        total_candidates += len(candidates)

        fields_out.append(FieldCandidates(
            field_id=field_id,
            label=label,
            target_unit=target_unit,
            candidates=candidates,
            selected_candidate=selected,
        ))

    return Agent1Result(
        document_id=payload.document_id,
        file_name=payload.file_name,
        fields=fields_out,
        total_candidates=total_candidates,
        selected_count=selected_count,
        review_count=review_count,
    )


def _extract_json(content: str) -> str:
    """Extract JSON from LLM response (handles markdown code blocks)."""
    content = content.strip()
    # Remove markdown code blocks
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:])  # Remove first line (```json)
        if content.endswith("```"):
            content = content[:-3]
    return content.strip()


def run(
    payload: CamelotPayload,
    artifact_paths: ArtifactPaths,
    enriched_payload: EnrichedPayloadModel | None = None,
) -> Agent1Result:
    """
    Run Step 1: Agent 1 Candidate Selection.

    Args:
        payload: CamelotPayload from Step 0
        artifact_paths: Artifact paths manager
        enriched_payload: EnrichedPayload from Step 0.5 (optional)

    Returns:
        Agent1Result
    """
    logger.info(f"Step 1: Running Agent 1 candidate selection for {payload.file_name}")

    target_fields = _load_target_fields()
    llm_input = _build_llm_input(payload, target_fields, enriched_payload=enriched_payload)

    # Save prompt
    prompt_path = artifact_paths.step1_prompt("batch")
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(_load_prompt() + "\n\n# LLM INPUT\n" + llm_input, encoding="utf-8")

    # Call LLM
    response_path = artifact_paths.step1_response("batch")
    try:
        content = _call_llm(llm_input, response_path)
    except RuntimeError as e:
        logger.error(f"Step 1 LLM call failed: {e}")
        raise

    # Parse output
    result = _parse_llm_output(content, payload)

    # Save result
    save_agent1(result, artifact_paths.step1_candidates())

    logger.info(f"Step 1: Found {result.total_candidates} candidates "
                f"({result.selected_count} selected, {result.review_count} review)")

    return result


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 3:
        print("Usage: python3 step1_agent_candidate.py <payload_json> <output_dir>")
        sys.exit(1)

    payload_path = sys.argv[1]
    output_dir = Path(sys.argv[2])

    from artifacts import ArtifactPaths
    payload = load_payload(Path(payload_path))
    pdf_stem = Path(payload.file_name).stem
    ap = ArtifactPaths(output_dir, pdf_stem).ensure_dirs()

    result = run(payload, ap)
    print(f"\nStep 1: {result.total_candidates} candidates, "
          f"{result.selected_count} selected, {result.review_count} review")
    print(f"Result saved to: {ap.step1_candidates()}")
