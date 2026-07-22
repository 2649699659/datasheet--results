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
import json
import logging
import time
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

from .contracts import WorkflowResult
from .artifacts import ArtifactPaths, load_payload, load_agent1, load_agent2, load_agent3, save_workflow_result

logger = logging.getLogger(__name__)


def run_workflow(
    pdf_path: str,
    output_dir: str,
    disable_context_enrichment: bool = False,
    allow_context_enrichment_fallback: bool = False,
    finalizer_mode: str = "shadow",
) -> WorkflowResult:
    """
    Run the full Agent Workflow for a single PDF.

    Steps:
        0. Extract tables with Camelot → CamelotPayload
        0.5. Enrich context (row classification, conditions, manufacturer)
        1. Agent 1: Candidate row selection → Agent1Result
        2. Agent 2: Parameter validation → Agent2Result
        2.5. Shadow Finalizer (Phase 4.1) - generates shadow artifacts
        3. Agent 3: Cross-parameter consistency → Agent3Result
        4. Write Excel report

    Args:
        pdf_path: Path to input PDF
        output_dir: Output directory for artifacts and Excel
        disable_context_enrichment: Skip Step 0.5 entirely
        allow_context_enrichment_fallback: If Step 0.5 fails, continue with raw payload

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
    enrichment_status = "disabled"

    # ── Step 0: Camelot Extraction ──────────────────────────────────────────
    try:
        from .steps.step0_build_camelot_payload import run as step0_run
        payload = step0_run(pdf_path, ap)
        if not payload.pages:
            raise RuntimeError("No tables extracted from PDF")
        table_count = sum(len(p.tables) for p in payload.pages)
        row_count = sum(len(t.rows) for p in payload.pages for t in p.tables)
        logger.info(f"Step 0: Camelot extraction — Tables: {table_count}, Rows: {row_count}")
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

    # ── Step 0.5: Context Enrichment ───────────────────────────────────────
    enriched_payload = None
    if disable_context_enrichment:
        logger.info("Context enrichment: disabled (--disable-context-enrichment)")
        enrichment_status = "disabled"
    else:
        try:
            from .steps.step0_5_enrich_context import run as step0_5_run
            enriched_payload = step0_5_run(payload, ap)
            enrichment_status = "success"
            logger.info(
                f"Step 0.5: Context enrichment — "
                f"Manufacturer: {enriched_payload.document_metadata.get('manufacturer', {}).get('canonical_value', 'N/A')}, "
                f"Heading conditions: {enriched_payload.heading_conditions_applied}, "
                f"Shared propagated: {enriched_payload.shared_conditions_propagated}"
            )
        except Exception as e:
            logger.error(f"Step 0.5 failed: {e}")
            if allow_context_enrichment_fallback:
                enrichment_status = "fallback"
                logger.warning(
                    f"Context enrichment: failed, falling back to raw Camelot payload "
                    f"(--allow-context-enrichment-fallback was set)"
                )
                warnings.append(f"Step 0.5 failed: {e}, using raw payload")
            else:
                enrichment_status = "failed"
                errors.append(f"Step 0.5 failed: {e} (use --allow-context-enrichment-fallback to ignore)")
                return WorkflowResult(
                    pdf_path=pdf_path,
                    output_xlsx="",
                    status="failed",
                    agent1=None, agent2=None, agent3=None,
                    errors=errors,
                    warnings=warnings,
                    elapsed_seconds=time.time() - start_time,
                )

    # ── Step 1: Agent 1 — Candidate Selection ───────────────────────────────
    try:
        from .steps.step1_agent_candidate import run as step1_run
        agent1 = step1_run(payload, ap, enriched_payload=enriched_payload)
        logger.info(
            f"Step 1: Candidate selection — "
            f"{agent1.selected_count} selected, {agent1.review_count} review "
            f"(enrichment: {enrichment_status})"
        )
    except Exception as e:
        logger.error(f"Step 1 failed: {e}")
        warnings.append(f"Step 1 (Agent 1) failed: {e}")
        agent1 = None

    # ── Step 2: Agent 2 — Validation ────────────────────────────────────────
    agent2 = None
    if agent1 is not None:
        try:
            from .steps.step2_agent_validator import run as step2_run
            agent2 = step2_run(agent1, ap, enriched_payload=enriched_payload)
        except Exception as e:
            logger.error(f"Step 2 failed: {e}")
            warnings.append(f"Step 2 (Agent 2) failed: {e}")

    # ── Step 2.5: Shadow Finalizer (Phase 4.1) ─────────────────────────────
    shadow_finalizer_result = None
    if agent2 is not None and agent1 is not None and finalizer_mode != "off":
        try:
            from .postprocess import ShadowFinalizer, FinalizerMode
            from .postprocess.final_result_materializer import load_target_fields_config
            
            mode = FinalizerMode(finalizer_mode)
            
            # Load target fields config
            target_fields = load_target_fields_config()
            
            # Run Shadow Finalizer
            finalizer = ShadowFinalizer(
                agent2_result=agent2.to_dict(),
                agent1_result=agent1.to_dict(),
                enriched_payload=enriched_payload.to_dict() if enriched_payload else {},
                target_fields_config=target_fields,
            )
            shadow_finalizer_result = finalizer.run(mode=mode)
            
            # Save shadow artifacts
            shadow_dir = ap.step0_5_report().parent
            
            # step2_5_finalized_shadow.json
            shadow_shadow_path = shadow_dir / "step2_5_finalized_shadow.json"
            shadow_shadow_path.write_text(
                json.dumps(shadow_finalizer_result.get("finalized_results", {}), indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            logger.info(f"Shadow Finalizer: Saved shadow to {shadow_shadow_path}")
            
            # step2_5_diff.json
            shadow_diff_path = shadow_dir / "step2_5_diff.json"
            shadow_diff_path.write_text(
                json.dumps(shadow_finalizer_result.get("diffs", []), indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            
            # step2_5_report.json
            shadow_report_path = shadow_dir / "step2_5_report.json"
            shadow_report_path.write_text(
                json.dumps(shadow_finalizer_result.get("report", {}), indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            
            logger.info(
                f"Shadow Finalizer: mode={finalizer_mode}, "
                f"fields={shadow_finalizer_result.get('report', {}).get('total_target_fields', 0)}, "
                f"changes={len(shadow_finalizer_result.get('diffs', []))}"
            )

            # ── ENFORCE MODE: Apply finalized results to agent2 ──────────────────
            if finalizer_mode == "enforce" and shadow_finalizer_result:
                from .contracts import Agent2Param
                finalized = shadow_finalizer_result.get("finalized_results", {})

                # Convert finalized_results dict to list of Agent2Param
                new_final_params = []
                for field_id, result_dict in finalized.items():
                    # Parse source_row_id to get source_page, table_index, row_index
                    source_page = None
                    table_index = None
                    row_index = None
                    source_text = None

                    source_row_id = result_dict.get("source_row_id")
                    if source_row_id and isinstance(source_row_id, str):
                        # Format: "p{p}_t{t}_r{r}" or "page_{p}_row_{r}"
                        parts = source_row_id.replace("p", "").replace("page_", "").split("_t")
                        if len(parts) >= 1:
                            page_part = parts[0].replace("page_", "").replace("p", "")
                            try:
                                source_page = int(page_part)
                            except ValueError:
                                pass
                        if len(parts) >= 2:
                            table_row = parts[1].split("_r")
                            if len(table_row) >= 1:
                                try:
                                    table_index = int(table_row[0])
                                except ValueError:
                                    pass
                            if len(table_row) >= 2:
                                try:
                                    row_index = int(table_row[1].replace("r", ""))
                                except ValueError:
                                    pass

                    # Parse status from result_dict
                    status_val = result_dict.get("status", "missing")
                    from .contracts import FieldStatus
                    try:
                        status = FieldStatus(status_val)
                    except ValueError:
                        status = FieldStatus.MISSING

                    param = Agent2Param(
                        field_id=field_id,
                        status=status,
                        value=result_dict.get("value"),
                        min=result_dict.get("min"),
                        typ=result_dict.get("typ"),
                        max=result_dict.get("max"),
                        unit=result_dict.get("unit"),
                        condition=result_dict.get("condition"),
                        source_page=source_page,
                        table_index=table_index,
                        row_index=row_index,
                        source_text=source_text,
                        confidence=result_dict.get("confidence", 0.0),
                        reason=result_dict.get("reason", ""),
                        warnings=result_dict.get("warnings", []),
                        missing_reason=result_dict.get("missing_reason"),
                    )
                    new_final_params.append(param)

                # Replace agent2.final_params with the new finalized params
                agent2.final_params = new_final_params
                logger.info(f"Enforce mode: Applied {len(new_final_params)} finalized params to agent2")
        except Exception as e:
            logger.error(f"Shadow Finalizer failed: {e}")
            warnings.append(f"Shadow Finalizer failed: {e}")
            import traceback
            traceback.print_exc()

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
    _print_summary(result, enrichment_status=enrichment_status)

    return result


def _print_summary(result: WorkflowResult, enrichment_status: str = "disabled"):
    """Print a concise summary."""
    print()
    print("=" * 60)
    print("WORKFLOW SUMMARY")
    print("=" * 60)
    print(f"  PDF:       {Path(result.pdf_path).name}")
    print(f"  Status:    {result.status.upper()}")
    print(f"  Elapsed:   {result.elapsed_seconds:.1f}s")
    print(f"  Context enrichment: {enrichment_status}")
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
    parser.add_argument(
        "--disable-context-enrichment",
        action="store_true",
        help="Skip Step 0.5 context enrichment (use raw Camelot payload)",
    )
    parser.add_argument(
        "--allow-context-enrichment-fallback",
        action="store_true",
        help="If Step 0.5 fails, continue with raw Camelot payload instead of aborting",
    )
    parser.add_argument(
        "--finalizer-mode",
        choices=["off", "shadow", "enforce"],
        default="shadow",
        help="Finalizer mode: off=skip, shadow=generate artifacts only, enforce=replace Step 3/4 input (default: shadow)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    result = run_workflow(
        args.pdf,
        args.output,
        disable_context_enrichment=args.disable_context_enrichment,
        allow_context_enrichment_fallback=args.allow_context_enrichment_fallback,
        finalizer_mode=args.finalizer_mode,
    )

    if result.status == "failed":
        return 1
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
