#!/usr/bin/env python3
"""
Datasheet Extractor - CLI Entry Point

Usage:
    python3 main.py --input datasheets/ --output output/final_comparison.xlsx
    python3 main.py --pdf datasheets/sample.pdf --output output/final_comparison.xlsx
    python3 main.py --validate-config
    python3 main.py --test-units
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.extractor import (
    extract_pdf,
    extract_pdfs_from_directory,
    process_page_tables,
    create_debug_output,
    print_summary,
)
from pipeline.parser import (
    parse_table_candidates,
    candidates_to_debug_json,
    generate_candidate_audit,
)
from pipeline.value_parser import (
    parse_candidate_values,
    params_to_debug_json,
    generate_value_parse_audit,
    extract_unit,
)
from utils.config_loader import (
    load_target_fields,
    get_field_ids,
    print_validation_report,
)
from utils.unit_converter import test_conversions
from pipeline.final_selector import (
    select_final_candidates,
    generate_selector_audit,
    save_selection_json,
)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Datasheet Extractor - Extract parameters from PDF datasheets to Excel"
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="Input directory containing PDF datasheets"
    )
    
    parser.add_argument(
        "--pdf", "-p",
        type=str,
        help="Single PDF file path"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output directory or file path"
    )
    
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Enable LLM enhancement (requires API key in .env)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output"
    )
    
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="Validate target_fields.yaml configuration"
    )
    
    parser.add_argument(
        "--test-units",
        action="store_true",
        help="Test unit conversion functions"
    )
    
    return parser.parse_args()


def validate_config():
    """Validate the target_fields.yaml configuration."""
    print("\nValidating target_fields.yaml configuration...\n")
    
    # Load and validate
    fields, errors = load_target_fields()
    
    # Print report
    print_validation_report(fields, errors)
    
    # Return exit code
    return 0 if len(errors) == 0 else 1


def test_units():
    """Test unit conversion and extraction functions."""
    print("\nTesting unit conversions...\n")
    
    all_passed, results = test_conversions()
    
    for result in results:
        print(result)
    
    print("\nTesting unit extraction (longest-first)...\n")
    
    # Unit extraction tests - verify longest-first ordering
    unit_tests = [
        ("5 kV", "kV"),
        ("10 mA", "mA"),
        ("5.3 mΩ", "mΩ"),
        ("0.3 °C/W", "°C/W"),
        ("8500 μJ", "μJ"),
        ("1200 V", "V"),
        ("300 A", "A"),
        ("25 °C", "°C"),
        ("1.5 K/W", "K/W"),
        ("100 ns", "ns"),
        ("39.6 pF", "pF"),
        ("20 nH", "nH"),
        ("9.5 g", "g"),
        ("2.3 mΩ", "mΩ"),
    ]
    
    unit_passed = 0
    for text, expected in unit_tests:
        result = extract_unit(text)
        status = "✓" if result == expected else "✗"
        if result == expected:
            unit_passed += 1
        print(f"  {status} extract_unit('{text}') = '{result}' (expected: '{expected}')")
    
    total_tests = len(unit_tests)
    print(f"\nUnit extraction: {unit_passed}/{total_tests} passed")
    
    overall_passed = all_passed and (unit_passed == total_tests)
    
    print()
    if overall_passed:
        print("Conversion test PASSED")
    else:
        print("Conversion test FAILED")
    
    return 0 if overall_passed else 1


def main():
    """Main entry point."""
    args = parse_args()
    
    # Handle --validate-config
    if args.validate_config:
        return validate_config()
    
    # Handle --test-units
    if args.test_units:
        return test_units()
    
    # Validate that output is specified for normal operation
    if not args.output:
        print("Error: --output is required (or use --validate-config)")
        sys.exit(1)
    
    # Validate inputs
    if not args.input and not args.pdf:
        print("Error: Must specify either --input or --pdf")
        sys.exit(1)
    
    if args.input and args.pdf:
        print("Error: Cannot specify both --input and --pdf")
        sys.exit(1)
    
    input_path = args.input or args.pdf
    output_path = Path(args.output)
    
    print(f"Datasheet Extractor")
    print(f"==================")
    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    print(f"LLM: {'Enabled' if args.llm else 'Disabled (not implemented yet)'}")
    print()
    
    # ========== Step 1: Extract PDFs ==========
    print("Step 1: Extracting PDFs...")
    
    if Path(input_path).is_file():
        # Single PDF
        extraction_results = [extract_pdf(input_path)]
    else:
        # Directory of PDFs
        extraction_results = extract_pdfs_from_directory(input_path)
    
    print(f"  Extracted {len(extraction_results)} PDF(s)")
    
    # ========== Step 2: Create Debug Output ==========
    print("\nStep 2: Creating debug output...")
    
    # Create output directory
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Always use fixed debug JSON path in output directory
    debug_json_path = output_path.parent / "debug_extracted_pages.json"
    
    # Create debug output
    debug_output = create_debug_output(extraction_results)
    
    # Save debug JSON
    with open(debug_json_path, "w", encoding="utf-8") as f:
        json.dump(debug_output, f, ensure_ascii=False, indent=2)
    
    print(f"  Debug JSON saved to: {debug_json_path}")
    
    # ========== Step 2b: Process Tables (needed for parser) ==========
    print("\nStep 2b: Processing tables...")
    
    processed_pdfs = []
    for result in extraction_results:
        if "error" in result:
            continue
        processed_pages = []
        for page_data in result.get("pages", []):
            processed_page = process_page_tables(page_data)
            processed_pages.append(processed_page)
        processed_pdfs.append({
            **result,
            "pages": processed_pages,
        })
    
    print(f"  Processed {len(processed_pdfs)} PDFs with table normalization")
    
    # ========== Step 3: Parse Candidates ==========
    print("\nStep 3: Parsing table candidates...")
    
    # Load target fields
    target_fields, field_errors = load_target_fields()
    if field_errors:
        print(f"  Warning: {len(field_errors)} field validation errors")
    
    # Parse candidates from PROCESSED data (not debug JSON)
    all_candidates = []
    all_rejected = {}  # Aggregate rejected info across all PDFs
    for processed_pdf in processed_pdfs:
        if "error" in processed_pdf:
            continue
        candidates, rejected = parse_table_candidates(processed_pdf, target_fields)
        all_candidates.extend(candidates)
        # Merge rejected info
        for key, info in rejected.items():
            if key not in all_rejected:
                all_rejected[key] = dict(info)
                all_rejected[key]["count"] = 0
                all_rejected[key]["examples"] = []
            all_rejected[key]["count"] += info["count"]
            for ex in info.get("examples", []):
                if len(all_rejected[key]["examples"]) < 3:
                    all_rejected[key]["examples"].append(ex)
    
    print(f"  Found {len(all_candidates)} candidate rows")
    print(f"  Rejected by rating guard: {sum(r.get('count', 0) for r in all_rejected.values())} rows")
    
    # Create candidates debug JSON
    all_target_field_ids = set(f["id"] for f in target_fields)
    candidates_debug = candidates_to_debug_json(all_candidates, extraction_results, all_target_field_ids, all_rejected)
    candidates_json_path = output_path.parent / "raw_candidates_debug.json"
    
    with open(candidates_json_path, "w", encoding="utf-8") as f:
        json.dump(candidates_debug, f, ensure_ascii=False, indent=2)
    
    print(f"  Candidates JSON saved to: {candidates_json_path}")
    
    # Generate candidate audit markdown
    audit_markdown = generate_candidate_audit(all_candidates, target_fields, candidates_debug, all_rejected)
    audit_path = output_path.parent / "candidate_audit.md"
    with open(audit_path, "w", encoding="utf-8") as f:
        f.write(audit_markdown)
    
    print(f"  Candidate audit saved to: {audit_path}")
    
    # ========== Step 5: Parse Candidate Values ==========
    print("\nStep 5: Parsing candidate values...")
    parsed_params = parse_candidate_values(all_candidates, extraction_results)
    
    # Generate raw params debug JSON
    params_debug = params_to_debug_json(parsed_params, all_candidates)
    params_json_path = output_path.parent / "raw_params_debug.json"
    with open(params_json_path, "w", encoding="utf-8") as f:
        json.dump(params_debug, f, ensure_ascii=False, indent=2)
    print(f"  Params JSON saved to: {params_json_path}")
    
    # Generate value parse audit markdown
    value_audit_markdown = generate_value_parse_audit(parsed_params, all_candidates, all_target_field_ids)
    value_audit_path = output_path.parent / "value_parse_audit.md"
    with open(value_audit_path, "w", encoding="utf-8") as f:
        f.write(value_audit_markdown)
    print(f"  Value parse audit saved to: {value_audit_path}")
    
    # Generate excel readiness audit (Step 5.7 checkpoint)
    readiness_markdown = generate_excel_readiness_audit(parsed_params, all_target_field_ids)
    readiness_path = output_path.parent / "excel_readiness_audit.md"
    with open(readiness_path, "w", encoding="utf-8") as f:
        f.write(readiness_markdown)
    print(f"  Excel readiness audit saved to: {readiness_path}")
    
    # Compute stats for summary
    parsed_value_count = params_debug["parsed_value_count"]
    failed_parse_count = params_debug["failed_parse_count"]
    
    # Collect fields with/without values
    fields_with_values = set()
    fields_without_values = set()
    for pdf_info in params_debug.get("pdfs", []):
        for fid in pdf_info.get("parsed_fields", []):
            fields_with_values.add(fid)
        for fid in pdf_info.get("failed_fields", []):
            fields_without_values.add(fid)
    
    # ========== Print Summary ==========
    print_summary(extraction_results, debug_output)
    
    # Compute warnings from candidates
    possible_overmatching = []
    fuzzy_only = []
    
    # Group candidates by field
    from collections import defaultdict
    by_field = defaultdict(list)
    for c in all_candidates:
        by_field[c.field_id].append(c)
    
    for field_id, field_candidates in by_field.items():
        # Check overmatching (> 8 candidates)
        if len(field_candidates) > 8:
            possible_overmatching.append(field_id)
        
        # Check fuzzy only
        match_types = set()
        for c in field_candidates:
            if c.confidence == 0.95:
                match_types.add("exact")
            elif c.confidence == 0.85:
                match_types.add("symbol")
            elif c.confidence == 0.70:
                match_types.add("fuzzy")
        
        if "fuzzy" in match_types and "exact" not in match_types and "symbol" not in match_types:
            fuzzy_only.append(field_id)
    
    # Print candidates summary
    print("\n" + "=" * 60)
    print("CANDIDATES SUMMARY")
    print("=" * 60)
    print(f"  Processed PDFs:           {len(extraction_results)}")
    print(f"  Total candidate rows:     {len(all_candidates)}")
    
    # Count matched fields
    all_field_ids = set(c.field_id for c in all_candidates)
    target_field_ids = set(f["id"] for f in target_fields)
    
    print(f"  Matched fields:           {len(all_field_ids)}")
    print(f"  Unmatched fields:          {len(target_field_ids - all_field_ids)}")
    
    if all_field_ids:
        print(f"\n  Matched field IDs:")
        for fid in sorted(all_field_ids)[:10]:
            count = sum(1 for c in all_candidates if c.field_id == fid)
            print(f"    - {fid}: {count} candidates")
        if len(all_field_ids) > 10:
            print(f"    ... and {len(all_field_ids) - 10} more")
    
    if target_field_ids - all_field_ids:
        print(f"\n  Fields with zero candidates:")
        for fid in sorted(target_field_ids - all_field_ids):
            print(f"    - {fid}")
    
    if possible_overmatching:
        print(f"\n  Possible overmatching (>8 candidates):")
        for fid in sorted(possible_overmatching)[:10]:
            count = sum(1 for c in all_candidates if c.field_id == fid)
            print(f"    - {fid}: {count} candidates")
    
    if fuzzy_only:
        print(f"\n  Fuzzy only match (no exact/symbol):")
        for fid in sorted(fuzzy_only):
            count = sum(1 for c in all_candidates if c.field_id == fid)
            print(f"    - {fid}: {count} candidates")
    
    print("=" * 60)
    print(f"\nDebug JSON path: {debug_json_path}")
    print(f"Candidates JSON path: {candidates_json_path}")
    print(f"Candidate audit path: {audit_path}")
    print(f"Params JSON path: {params_json_path}")
    print(f"Value parse audit path: {value_audit_path}")
    
    # Print value parsing summary
    active_count = sum(1 for c in all_candidates if c.candidate_status == "active")
    print(f"\nVALUE PARSING SUMMARY")
    print("=" * 60)
    print(f"  Active candidates:          {active_count}")
    print(f"  Parsed values:             {parsed_value_count}")
    print(f"  Failed to parse:           {failed_parse_count}")
    print(f"  Fields with values:        {len(fields_with_values)}")
    print(f"  Fields without values:     {len(fields_without_values)}")
    if fields_with_values:
        print(f"\n  Fields with parsed values:")
        for fid in sorted(fields_with_values)[:10]:
            count = sum(1 for p in parsed_params if p.field_id == fid and (p.typ is not None or p.min is not None or p.max is not None or p.value is not None))
            print(f"    - {fid}: {count}")
        if len(fields_with_values) > 10:
            print(f"    ... and {len(fields_with_values) - 10} more")
    if fields_without_values:
        print(f"\n  Fields without parsed values:")
        for fid in sorted(fields_without_values)[:10]:
            print(f"    - {fid}")
        if len(fields_without_values) > 10:
            print(f"    ... and {len(fields_without_values) - 10} more")
    print("=" * 60)
    
    # ========== Step 6: Final Selector ==========
    print("\nStep 6: Selecting final candidates...")
    
    # Run final selector
    selection_result = select_final_candidates(parsed_params, target_fields)
    
    # Save selection debug JSON
    selection_json_path = output_path.parent / "selected_params_debug.json"
    save_selection_json(selection_result, str(selection_json_path))
    print(f"  Selection JSON saved to: {selection_json_path}")
    
    # Generate selector audit markdown
    selector_audit_markdown = generate_selector_audit(selection_result)
    selector_audit_path = output_path.parent / "selector_audit.md"
    with open(selector_audit_path, "w", encoding="utf-8") as f:
        f.write(selector_audit_markdown)
    print(f"  Selector audit saved to: {selector_audit_path}")
    
    # Print selector summary
    print(f"\nSELECTION SUMMARY (Step 6)")
    print("=" * 60)
    print(f"  Total fields:           {selection_result['field_count']}")
    print(f"  final_candidate:        {selection_result['final_candidate_count']}")
    print(f"  review_needed:         {selection_result['review_needed_count']}")
    print(f"  blocked:               {selection_result['blocked_count']}")
    print(f"  missing:                {selection_result['missing_count']}")
    print("=" * 60)
    
    if selection_result['final_candidate_count'] > 0:
        print(f"\n  Final Candidates:")
        for f in selection_result["fields"]:
            if f["selection_status"] == "final_candidate":
                p = f["selected_param"]
                val_parts = []
                if p.get("min") is not None: val_parts.append(f"min={p['min']}")
                if p.get("typ") is not None: val_parts.append(f"typ={p['typ']}")
                if p.get("max") is not None: val_parts.append(f"max={p['max']}")
                if p.get("value") is not None: val_parts.append(f"val={p['value']}")
                val_str = ", ".join(val_parts) if val_parts else "-"
                print(f"    - {f['field_id']}: {val_str} {p.get('original_unit', '')} (score={f['selector_score']})")
    
    print("\nNOTE: This is Step 6 - Final Selector only.")
    print("      No unit conversion, no Excel generated yet.")
    
    return 0


def generate_excel_readiness_audit(parsed_params: list, target_field_ids: list) -> str:
    """
    Generate Excel readiness audit markdown report.
    
    Readiness rules:
    - ready_for_final: high quality AND no critical issues
    - review_only: some issues but not critical
    - blocked: has unit_mismatch, condition_type_mismatch, condition_unclear, etc.
    - missing: no candidates
    """
    from collections import defaultdict
    
    # Group params by field_id
    by_field = defaultdict(list)
    for p in parsed_params:
        by_field[p.field_id].append(p)
    
    # Target fields set
    target_set = set(target_field_ids) if target_field_ids else set()
    
    # Readiness classification
    ready_fields = []
    review_fields = []
    blocked_fields = []
    missing_fields = []
    
    # Critical issues that block ready_for_final
    CRITICAL_ISSUES = [
        "unit_mismatch",
        "condition_type_mismatch",
        "condition_unclear",
        "range_value_needs_review",
        "slash_list_value_needs_review",
        "ambiguous",
        "suspect",
        "value_column_suspect",
        "min_greater_than_max",
        "partial_threshold_values",
    ]
    
    for field_id in sorted(target_set):
        params = by_field.get(field_id, [])
        
        if not params:
            missing_fields.append(field_id)
            continue
        
        # Check for critical issues
        has_critical = False
        critical_details = []
        
        for p in params:
            rr = (p.review_reason or "").lower()
            for issue in CRITICAL_ISSUES:
                if issue in rr:
                    has_critical = True
                    critical_details.append(f"{field_id}: {issue} in {p.review_reason}")
        
        # Check parse_quality
        parse_qualities = set(p.parse_quality for p in params if hasattr(p, 'parse_quality'))
        
        # Check if any param has unit_mismatch from unit_warning
        has_unit_mismatch = any(
            getattr(p, 'unit_warning', '') and 'mismatch' in getattr(p, 'unit_warning', '').lower()
            for p in params
        )
        
        if has_critical or has_unit_mismatch:
            blocked_fields.append((field_id, params, critical_details))
        elif 'high' in parse_qualities and len(parse_qualities) == 1:
            ready_fields.append((field_id, params))
        else:
            review_fields.append((field_id, params))
    
    lines = []
    lines.append("# Excel Readiness Audit (Step 5.8)")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Category | Count |")
    lines.append(f"|----------|-------|")
    lines.append(f"| ready_for_final | {len(ready_fields)} |")
    lines.append(f"| review_only | {len(review_fields)} |")
    lines.append(f"| blocked | {len(blocked_fields)} |")
    lines.append(f"| missing (no candidates) | {len(missing_fields)} |")
    lines.append(f"| TOTAL | {len(ready_fields) + len(review_fields) + len(blocked_fields) + len(missing_fields)} |")
    lines.append("")
    
    # Readiness status
    overall_status = "NOT READY"
    if len(ready_fields) >= 25 and len(blocked_fields) <= 5:
        overall_status = "MOSTLY READY"
    elif len(ready_fields) >= 20 and len(blocked_fields) <= 10:
        overall_status = "PARTIALLY READY"
    
    lines.append(f"**Overall Status**: {overall_status}")
    lines.append("")
    
    # Ready for final fields
    lines.append("## ready_for_final")
    lines.append("")
    if ready_fields:
        lines.append(f"| Field ID | parse_quality | value |")
        lines.append(f"|----------|---------------|-------|")
        for field_id, params in ready_fields:
            values = []
            for p in params:
                if p.typ is not None:
                    values.append(f"typ={p.typ}")
                if p.min is not None:
                    values.append(f"min={p.min}")
                if p.max is not None:
                    values.append(f"max={p.max}")
                if p.value is not None:
                    values.append(f"val={p.value}")
            value_str = ", ".join(values) if values else "-"
            pq = ", ".join(set(p.parse_quality for p in params if hasattr(p, 'parse_quality')))
            lines.append(f"| {field_id} | {pq} | {value_str} |")
        lines.append("")
    else:
        lines.append("*No fields ready for final.*")
        lines.append("")
    
    # Review only fields
    lines.append("## review_only")
    lines.append("")
    if review_fields:
        lines.append(f"| Field ID | parse_quality | Issues |")
        lines.append(f"|----------|---------------|--------|")
        for field_id, params in review_fields:
            pq = ", ".join(set(p.parse_quality for p in params if hasattr(p, 'parse_quality')))
            issues = set()
            for p in params:
                rr = p.review_reason or ""
                for issue in ["from_text_fallback", "no_reliable_header", "partial", "condition_mismatch"]:
                    if issue in rr.lower():
                        issues.add(issue)
            issues_str = ", ".join(sorted(issues)) if issues else "-"
            lines.append(f"| {field_id} | {pq} | {issues_str} |")
        lines.append("")
    else:
        lines.append("*No review_only fields.*")
        lines.append("")
    
    # Blocked fields
    lines.append("## blocked")
    lines.append("")
    if blocked_fields:
        lines.append(f"| Field ID | Count | Critical Issues |")
        lines.append(f"|----------|-------|----------------|")
        for field_id, params, details in blocked_fields:
            issues = set()
            for p in params:
                rr = (p.review_reason or "").lower()
                for issue in CRITICAL_ISSUES:
                    if issue in rr:
                        issues.add(issue)
            issues_str = ", ".join(sorted(issues)) if issues else "-"
            lines.append(f"| {field_id} | {len(params)} | {issues_str} |")
        lines.append("")
    else:
        lines.append("*No blocked fields.*")
        lines.append("")
    
    # Missing fields
    lines.append("## missing (no candidates)")
    lines.append("")
    if missing_fields:
        lines.append(f"| Field ID |")
        lines.append(f"|----------|")
        for fid in sorted(missing_fields):
            lines.append(f"| {fid} |")
        lines.append("")
    else:
        lines.append("*No missing fields.*")
        lines.append("")
    
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
