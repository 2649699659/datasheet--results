"""
step2_agent_validator.py — Step 2: Agent 2 — Parameter Validation & Disambiguation

Reviews Agent 1 candidates and validates/corrects each parameter selection.
Uses the Agent 2 LLM prompt for parameter review.

Input:  Agent1Result (from Step 1)
Output: Agent2Result (validated final params)
"""

import json
import logging
from pathlib import Path

from ..contracts import (
    Agent1Result,
    Agent2Param,
    Agent2Result,
    FieldStatus,
)
from ..artifacts import ArtifactPaths, save_agent2, load_agent1
from ..enrichment.models import EnrichedPayload as EnrichedPayloadModel

logger = logging.getLogger(__name__)

# Load Agent 2 prompt
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "agent2_validator.md"


def _load_prompt() -> str:
    if PROMPT_PATH.exists():
        return PROMPT_PATH.read_text(encoding="utf-8")
    return ""


def _build_llm_input(
    agent1_result: Agent1Result,
    enriched_payload: EnrichedPayloadModel | None = None,
) -> str:
    """
    Build the LLM input from Agent 1 candidates.

    When enriched_payload is provided, includes:
    - resolved_condition per candidate row (from Phase 2A/3A)
    - condition_sources per candidate row
    - context_status per candidate row
    - manufacturer metadata from Phase 3B
    """
    lines = []
    lines.append(f"# Document: {agent1_result.file_name}\n")
    lines.append(f"# Document ID: {agent1_result.document_id}\n")

    # Add manufacturer metadata if available
    if enriched_payload is not None and enriched_payload.document_metadata:
        mfr = enriched_payload.document_metadata.get("manufacturer", {})
        if mfr:
            canonical = mfr.get("canonical_value", "N/A")
            status = mfr.get("status", "unknown")
            lines.append(f"# Manufacturer: {canonical} (status: {status})\n")

    lines.append("\n## Candidate Review Context\n")
    lines.append("Review each field's candidates and determine the correct selection.\n")
    lines.append("Output STRICT JSON:\n")

    lines.append("""```json
{
  "overall_status": "pass|needs_review|unsafe",
  "final_params": [
    {
      "field_id": "...",
      "status": "final|review_needed|blocked|missing",
      "value": null,
      "min": 2.0,
      "typ": null,
      "max": 4.0,
      "unit": "V",
      "condition": "VDS=VGS; ID=30mA",
      "source_page": 2,
      "table_index": 1,
      "row_index": 5,
      "source_text": "VGS(th) Gate Threshold Voltage 2 - 4 V VDS=VGS; ID=30mA",
      "confidence": 0.95,
      "reason": "...",
      "warnings": []
    }
  ],
  "summary": {
    "final_count": N,
    "review_needed_count": N,
    "missing_count": N,
    "blocked_count": N
  }
}
```""")

    lines.append("\n## Field Candidates\n")

    # Build enriched lookup if enriched_payload is available
    enriched_lookup: dict[tuple[int, int, int], object] = {}
    if enriched_payload is not None:
        for page in enriched_payload.pages:
            for table in page.tables:
                for row in table.rows:
                    key = (page.page_number, table.table_index, row.row_index)
                    enriched_lookup[key] = row

    for fc in agent1_result.fields:
        lines.append(f"\n### {fc.field_id} ({fc.label})\n")
        lines.append(f"Target unit: {fc.target_unit}\n")
        lines.append(f"Total candidates: {len(fc.candidates)}\n")

        for c in fc.candidates:
            status_marker = "★ SELECTED" if c == fc.selected_candidate else ""
            lines.append(f"\n  [{c.candidate_type.upper()}] {status_marker}")
            lines.append(f"  page={c.source_page}, table={c.table_index}, row={c.row_index}")
            lines.append(f"  cells: {c.row_cells}")
            lines.append(f"  confidence={c.confidence}, match_type={c.match_type}")
            if c.condition:
                lines.append(f"  raw_condition: {c.condition}")

            # Add enriched context if available
            if enriched_payload is not None:
                key = (c.source_page, c.table_index, c.row_index)
                enriched_row = enriched_lookup.get(key)
                if enriched_row is not None:
                    resolved_cond = getattr(enriched_row, 'resolved_condition', None)
                    if resolved_cond:
                        lines.append(f"  resolved_condition: {resolved_cond}")
                    condition_sources = getattr(enriched_row, 'condition_sources', [])
                    if condition_sources:
                        lines.append(f"  condition_sources: {condition_sources}")
                    ctx_status = getattr(enriched_row, 'context_status', None)
                    if ctx_status:
                        ctx_val = ctx_status.value if hasattr(ctx_status, 'value') else ctx_status
                        lines.append(f"  context_status: {ctx_val}")

            if c.review_reason:
                lines.append(f"  review_reason: {c.review_reason}")

    return "\n".join(lines)


def _call_llm(prompt: str, output_path: Path | None = None) -> str:
    """Call LLM with prompt."""
    import os

    if output_path and output_path.exists():
        logger.info(f"Reading cached response from {output_path}")
        return output_path.read_text(encoding="utf-8")

    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        raise RuntimeError("No API key found in MINIMAX_API_KEY or OPENAI_API_KEY")

    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.minimaxi.chat/v1")
    endpoint = f"{base_url.rstrip('/')}/chat/completions"

    import urllib.request
    data = {
        "model": os.environ.get("LLM_MODEL", "MiniMax-M2.7"),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
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
            if output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(content, encoding="utf-8")
            return content
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise RuntimeError(f"LLM API error {e.code}: {error_body}")


def _extract_json(content: str) -> str:
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:])
        if content.endswith("```"):
            content = content[:-3]
    return content.strip()


def _parse_llm_output(content: str) -> Agent2Result:
    """Parse LLM output into Agent2Result."""
    d = json.loads(_extract_json(content))

    params = []
    for p in d.get("final_params", []):
        status_str = p.get("status", "review_needed")
        status = FieldStatus(status_str) if status_str in ["final", "review_needed", "blocked", "missing"] else FieldStatus.REVIEW_NEEDED

        params.append(Agent2Param(
            field_id=p.get("field_id", ""),
            status=status,
            value=p.get("value"),
            min=p.get("min"),
            typ=p.get("typ"),
            max=p.get("max"),
            unit=p.get("unit"),
            condition=p.get("condition"),
            source_page=p.get("source_page"),
            table_index=p.get("table_index"),
            row_index=p.get("row_index"),
            source_text=p.get("source_text"),
            confidence=p.get("confidence", 0.0),
            reason=p.get("reason", ""),
            warnings=p.get("warnings", []),
        ))

    return Agent2Result(
        document_id=d.get("document_id", ""),
        file_name=d.get("file_name", ""),
        overall_status=d.get("overall_status", "needs_review"),
        final_params=params,
        summary=d.get("summary", {
            "final_count": sum(1 for p in params if p.status == FieldStatus.FINAL),
            "review_needed_count": sum(1 for p in params if p.status == FieldStatus.REVIEW_NEEDED),
            "missing_count": sum(1 for p in params if p.status == FieldStatus.MISSING),
            "blocked_count": sum(1 for p in params if p.status == FieldStatus.BLOCKED),
        }),
    )


def run(
    agent1_result: Agent1Result,
    artifact_paths: ArtifactPaths,
    enriched_payload: EnrichedPayloadModel | None = None,
) -> Agent2Result:
    """
    Run Step 2: Agent 2 Parameter Validation.

    Args:
        agent1_result: Agent1Result from Step 1
        artifact_paths: Artifact paths manager
        enriched_payload: EnrichedPayload from Step 0.5 (optional)

    Returns:
        Agent2Result
    """
    logger.info(f"Step 2: Running Agent 2 validation for {agent1_result.file_name}")

    llm_input = _build_llm_input(agent1_result, enriched_payload=enriched_payload)

    # Save prompt
    prompt_path = artifact_paths.step2_prompt()
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(_load_prompt() + "\n\n# LLM INPUT\n" + llm_input, encoding="utf-8")

    # Call LLM
    response_path = artifact_paths.step2_response()
    try:
        content = _call_llm(llm_input, response_path)
    except RuntimeError as e:
        logger.error(f"Step 2 LLM call failed: {e}")
        raise

    # Parse output
    result = _parse_llm_output(content)

    # Save result
    save_agent2(result, artifact_paths.step2_final_params())

    s = result.summary
    logger.info(f"Step 2: final={s.get('final_count',0)}, "
                f"review={s.get('review_needed_count',0)}, "
                f"missing={s.get('missing_count',0)}, "
                f"blocked={s.get('blocked_count',0)}")

    return result


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 3:
        print("Usage: python3 step2_agent_validator.py <agent1_json> <output_dir>")
        sys.exit(1)

    agent1_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])

    from artifacts import ArtifactPaths
    agent1 = load_agent1(agent1_path)
    pdf_stem = Path(agent1.file_name).stem
    ap = ArtifactPaths(output_dir, pdf_stem).ensure_dirs()

    result = run(agent1, ap)
    s = result.summary
    print(f"\nStep 2: final={s.get('final_count',0)}, "
          f"review={s.get('review_needed_count',0)}, "
          f"missing={s.get('missing_count',0)}, "
          f"blocked={s.get('blocked_count',0)}")
    print(f"Result saved to: {ap.step2_final_params()}")
