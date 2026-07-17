"""
artifacts.py — Intermediate file management for the Agent Workflow

Manages reading/writing of intermediate JSON files between steps.
Each step's output is stored as a separate JSON file.
"""

import json
import time
from pathlib import Path
from typing import Any, Callable

from .contracts import (
    CamelotPayload,
    Agent1Result,
    Agent2Result,
    Agent3Result,
    WorkflowResult,
)


# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────

class ArtifactPaths:
    """Generates standard artifact paths for a given run."""

    def __init__(self, output_dir: Path, pdf_stem: str):
        self.output_dir = Path(output_dir)
        self.pdf_stem = pdf_stem
        self.run_id = f"{pdf_stem}_{int(time.time())}"
        self.run_dir = self.output_dir / self.run_id
        self.prompts_dir = self.run_dir / "prompts"
        self.responses_dir = self.run_dir / "responses"
        self.artifacts_dir = self.run_dir / "artifacts"

    def ensure_dirs(self) -> "ArtifactPaths":
        """Create all directories."""
        for d in [self.run_dir, self.prompts_dir, self.responses_dir, self.artifacts_dir]:
            d.mkdir(parents=True, exist_ok=True)
        return self

    # Step 0: Camelot payload
    def step0_payload(self) -> Path:
        return self.artifacts_dir / "step0_camelot_payload.json"

    # Step 1: Agent 1 candidates
    def step1_candidates(self) -> Path:
        return self.artifacts_dir / "step1_agent1_candidates.json"

    def step1_prompt(self, field_id: str) -> Path:
        return self.prompts_dir / f"step1_{field_id}_prompt.md"

    def step1_response(self, field_id: str) -> Path:
        return self.responses_dir / f"step1_{field_id}_response.json"

    # Step 2: Agent 2 validated params
    def step2_final_params(self) -> Path:
        return self.artifacts_dir / "step2_agent2_final_params.json"

    def step2_prompt(self) -> Path:
        return self.prompts_dir / "step2_agent2_prompt.md"

    def step2_response(self) -> Path:
        return self.responses_dir / "step2_agent2_response.json"

    # Step 3: Agent 3 consistency
    def step3_consistency(self) -> Path:
        return self.artifacts_dir / "step3_agent3_consistency.json"

    # Step 4: Excel
    def step4_excel(self) -> Path:
        return self.run_dir / f"{self.pdf_stem}_final.xlsx"

    # Workflow result
    def workflow_result(self) -> Path:
        return self.artifacts_dir / "workflow_result.json"


# ─────────────────────────────────────────────────────────────────────────────
# Load/Save
# ─────────────────────────────────────────────────────────────────────────────

def save_payload(payload: CamelotPayload, path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload.to_dict(), f, ensure_ascii=False, indent=2)


def load_payload(path: Path) -> CamelotPayload:
    with open(path, encoding="utf-8") as f:
        return CamelotPayload.from_dict(json.load(f))


def save_agent1(result: Agent1Result, path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)


def load_agent1(path: Path) -> Agent1Result:
    # Reconstruct from dict (simplified — actual impl would deserialize properly)
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    from contracts import FieldCandidates, CandidateRow
    fields = []
    for fd in d["fields"]:
        candidates = [CandidateRow(**c) for c in fd["candidates"]]
        selected = CandidateRow(**fd["selected_candidate"]) if fd.get("selected_candidate") else None
        fields.append(FieldCandidates(
            field_id=fd["field_id"],
            label=fd["label"],
            target_unit=fd["target_unit"],
            candidates=candidates,
            selected_candidate=selected,
        ))
    return Agent1Result(
        document_id=d["document_id"],
        file_name=d["file_name"],
        fields=fields,
        total_candidates=d["total_candidates"],
        selected_count=d["selected_count"],
        review_count=d["review_count"],
    )


def save_agent2(result: Agent2Result, path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)


def load_agent2(path: Path) -> Agent2Result:
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    from contracts import Agent2Param, FieldStatus
    params = [
        Agent2Param(
            field_id=p["field_id"],
            status=FieldStatus(p["status"]) if p["status"] in [e.value for e in FieldStatus] else p["status"],
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
        )
        for p in d["final_params"]
    ]
    return Agent2Result(
        document_id=d["document_id"],
        file_name=d["file_name"],
        overall_status=d.get("overall_status", "needs_review"),
        final_params=params,
        summary=d.get("summary", {}),
    )


def save_agent3(result: Agent3Result, path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)


def load_agent3(path: Path) -> Agent3Result:
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    from contracts import ConsistencyCheck
    checks = [
        ConsistencyCheck(
            rule_id=c["rule_id"],
            rule_name=c["rule_name"],
            severity=c["severity"],
            status=c["status"],
            fields_involved=c["fields_involved"],
            details=c.get("details", {}),
            verdict=c["verdict"],
            suggested_action=c.get("suggested_action", "none"),
        )
        for c in d.get("consistency_checks", [])
    ]
    return Agent3Result(
        document_id=d["document_id"],
        file_name=d["file_name"],
        overall_status=d.get("overall_status", "review_needed"),
        consistency_checks=checks,
        summary=d.get("summary", {}),
        recommendations=d.get("recommendations", []),
    )


def save_workflow_result(result: WorkflowResult, path: Path) -> None:
    def safe_serializer(obj: Any) -> Any:
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "pdf_path": result.pdf_path,
            "output_xlsx": result.output_xlsx,
            "status": result.status,
            "errors": result.errors,
            "warnings": result.warnings,
            "elapsed_seconds": result.elapsed_seconds,
            "agent1_summary": result.agent1.to_dict() if result.agent1 else None,
            "agent2_summary": result.agent2.to_dict() if result.agent2 else None,
            "agent3_summary": result.agent3.to_dict() if result.agent3 else None,
        }, f, default=safe_serializer, ensure_ascii=False, indent=2)


def load_workflow_result(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────────────────────
# LLM Call helpers
# ─────────────────────────────────────────────────────────────────────────────

def call_llm(
    prompt: str,
    output_path: Path | None = None,
    model: str = "minimax/MiniMax-M2.7",
    temperature: float = 0.1,
) -> str:
    """
    Call the configured LLM with a prompt.

    Falls back to reading from output_path if file exists (for testing).
    """
    # Check for cached response
    if output_path and output_path.exists():
        with open(output_path, encoding="utf-8") as f:
            return f.read()

    import os
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("API_KEY")
    if not api_key:
        raise RuntimeError("No API key found in environment (OPENAI_API_KEY or API_KEY)")

    import urllib.request
    import urllib.parse

    # Build request
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(data).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"]
            if output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(content)
            return content
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise RuntimeError(f"LLM API error {e.code}: {error_body}")
