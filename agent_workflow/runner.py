"""
runner.py — Agent Workflow Runner

End-to-end orchestrator for the datasheet extraction pipeline.

Usage:
    python3 agent_workflow/runner.py --pdf path/to/datasheet.pdf --output output_dir/

Or import directly:
    from agent_workflow.runner import run_workflow
    result = run_workflow("/path/to/file.pdf", "/output/dir/")
"""

import argparse
import logging
import time
from pathlib import Path
from typing import Literal

from .contracts import WorkflowResult
from .artifacts import ArtifactPaths, load_payload, load_agent1, load_agent2, load_agent3, save_workflow_result

logger = logging.getLogger(__name__)


def run_workflow(
    pdf_path: str,
    output_dir: str,
) -> WorkflowResult:
    """
    Run the full Agent Workflow for a single PDF.

    Steps:
        0. Extract tables with Camelot → CamelotPayload
        1. Agent 1: Candidate row selection → Agent1Result
        2. Agent 2: Parameter validation → Agent2Result
        3. Agent 3: Cross-parameter consistency → Agent3Result
        4. Write Excel report

    Args:
        pdf_path: Path to input PDF
        output_dir: Output directory for artifacts and Excel

    Returns:
        WorkflowResult with all outputs
    """
    start_time = time.time()
    pdf_stem = Path(pdf_path).stem

    output_dir = Path(output_dir)
    ap = ArtifactPaths(output_dir, pdf_stem).ensure_dirs()

    logger.info("=" * 60)
    logger.info(f"Agent Workflow: {pdf_path}")
    logger.info(f"Output dir: {ap.run_dir}")
    logger.info("=" * 60)

    errors: list[str] = []
    warnings: list[str] = []

    # ── Step 0: Camelot Extraction ──────────────────────────────────────────
    try:
        from .steps.step0_build_camelot_payload import run as step0_run
        payload = step0_run(pdf_path, ap)
        if not payload.pages:
            raise RuntimeError("No tables extracted from PDF")
    except Exception as e:
        logger.error(f"Step 0 failed: {e}")
        return WorkflowResult(
            pdf_path=pdf_path,
            output_xlsx="",
            status="failed",
            agent1=None, agent2=None, agent3=None,
            errors=[str(e)],
            elapsed_seconds=time.time() - start_time,
        )

    # ── Step 1: Agent 1 — Candidate Selection ───────────────────────────────
    try:
        from .steps.step1_agent_candidate import run as step1_run
        agent1 = step1_run(payload, ap)
    except Exception as e:
        logger.error(f"Step 1 failed: {e}")
        warnings.append(f"Step 1 (Agent 1) failed: {e}")
        agent1 = None

    # ── Step 2: Agent 2 — Validation ────────────────────────────────────────
    agent2 = None
    if agent1 is not None:
        try:
            from .steps.step2_agent_validator import run as step2_run
            agent2 = step2_run(agent1, ap)
        except Exception as e:
            logger.error(f"Step 2 failed: {e}")
            warnings.append(f"Step 2 (Agent 2) failed: {e}")

    # ── Step 3: Agent 3 — Consistency Check ─────────────────────────────────
    agent3 = None
    if agent2 is not None:
        try:
            from .steps.step3_agent_cross_check import run as step3_run
            agent3 = step3_run(agent2, ap)
        except Exception as e:
            logger.error(f"Step 3 failed: {e}")
            warnings.append(f"Step 3 (Agent 3) failed: {e}")

    # ── Step 4: Excel Generation ────────────────────────────────────────────
    excel_path = ""
    if agent2 is not None and agent3 is not None:
        try:
            from .steps.step4_write_excel import run as step4_run
            excel_path = str(step4_run(agent2, agent3, ap))
        except Exception as e:
            logger.error(f"Step 4 failed: {e}")
            warnings.append(f"Step 4 (Excel) failed: {e}")

    elapsed = time.time() - start_time

    # Determine status
    if agent2 is None:
        status = "failed"
    elif agent3 is None:
        status = "partial"
    else:
        status = "success"

    # Build result
    result = WorkflowResult(
        pdf_path=pdf_path,
        output_xlsx=excel_path,
        status=status,
        agent1=agent1,
        agent2=agent2,
        agent3=agent3,
        errors=errors,
        warnings=warnings,
        elapsed_seconds=elapsed,
    )

    # Save result
    try:
        save_workflow_result(result, ap.workflow_result())
    except Exception as e:
        logger.warning(f"Could not save workflow result: {e}")

    # Print summary
    _print_summary(result)

    return result


def _print_summary(result: WorkflowResult):
    """Print a concise summary."""
    print()
    print("=" * 60)
    print("WORKFLOW SUMMARY")
    print("=" * 60)
    print(f"  PDF:       {Path(result.pdf_path).name}")
    print(f"  Status:    {result.status.upper()}")
    print(f"  Elapsed:   {result.elapsed_seconds:.1f}s")
    if result.agent1:
        print(f"  Agent 1:  {result.agent1.total_candidates} candidates "
              f"({result.agent1.selected_count} selected, {result.agent1.review_count} review)")
    if result.agent2:
        s = result.agent2.summary
        print(f"  Agent 2:  final={s.get('final_count',0)}, "
              f"review={s.get('review_needed_count',0)}, "
              f"blocked={s.get('blocked_count',0)}, "
              f"missing={s.get('missing_count',0)}")
    if result.agent3:
        s = result.agent3.summary
        print(f"  Agent 3:  {s.get('passed',0)}/{s.get('total_checks',0)} checks passed, "
              f"{s.get('warnings',0)} warnings, {s.get('failed',0)} failed")
    if result.output_xlsx:
        print(f"  Excel:    {result.output_xlsx}")
    if result.warnings:
        print(f"  Warnings: {len(result.warnings)}")
        for w in result.warnings[:3]:
            print(f"    - {w}")
    if result.errors:
        print(f"  Errors:   {len(result.errors)}")
        for e in result.errors[:3]:
            print(f"    - {e}")
    print("=" * 60)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Agent Workflow — End-to-end datasheet extraction"
    )
    parser.add_argument("--pdf", "-p", required=True, help="Input PDF file path")
    parser.add_argument("--output", "-o", required=True, help="Output directory")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    return parser.parse_args()


def main():
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    result = run_workflow(args.pdf, args.output)

    if result.status == "failed":
        return 1
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
