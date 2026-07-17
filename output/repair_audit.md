# Repair Audit Report

**Generated**: 2026-07-16T15:54:45.401372

**Review File**: output/ai_parameter_review.json

**Selection File**: output/selected_params_debug.json

**Output File**: output/repaired_selection.json

## Summary

- Total fields reviewed: 30
- Source preserved: 28
- Values fabricated: 0

## Action Distribution (AI Suggested)

| Action | Count |
|--------|-------|
| add_warning | 2 |
| block_candidate | 1 |
| downgrade_to_review | 4 |
| keep | 16 |
| mark_missing | 4 |
| replace_selected_candidate | 3 |

## Action Distribution (Actually Applied)

| Action | Count |
|--------|-------|
| blocked_by_ai_review | 1 |
| downgraded_to_review | 4 |
| keep | 16 |
| marked_missing | 4 |
| replaced_selected_candidate | 2 |
| replacement_failed_no_candidate | 1 |
| warning_added | 2 |

## Fields Requiring Attention

### Successfully Replaced

| Field | Previous | New Status | Details |
|-------|----------|------------|--------|
| qg | review_needed | review_needed | Replaced with value=618.0 from source_text: QG Total Gate Charge - 618 - nC VDD= |
| junction_temperature | review_needed | review_needed | Replaced with value=175.0 from source_text: TJ; MAX Junction Temperature 175 C |

### Replacement Failed (No Candidate Found)

| Field | Reason |
|-------|--------|
| module_type | No candidate found matching hint: Module type should be 'ME3' from the Package Type row. Do not extr |

### Downgraded to Review

| Field | Reason |
|-------|--------|
| ciss | Changed from review_needed to review_needed |
| eoff | Changed from review_needed to review_needed |
| isol | Changed from review_needed to review_needed |
| clearance_tt | Changed from review_needed to review_needed |

### Blocked by AI Review

| Field | Reason |
|-------|--------|
| rds_on_150c | Changed from review_needed to blocked |

### Marked as Missing

| Field | Reason |
|-------|--------|
| manufacturer | Changed from missing to missing |
| part_number | Changed from review_needed to missing |
| err | Changed from missing to missing |
| rth_jc | Changed from blocked to missing |

### Warnings Added

| Field | Warning |
|-------|--------|
| eon | [AI_REVIEW_WARNING] condition_error: Selected value=7.1 mJ from Eon row with conditions 'VDS=800V; I |
| qrr | [AI_REVIEW_WARNING] correct: Selected value=1839 nC (displayed as μC due to unit conversion issue) f |

### Critical/High Severity Fields

| Field | Severity | Verdict | Action Taken |
|-------|----------|---------|--------------|
| part_number | critical | wrong_candidate | marked_missing |
| module_type | critical | wrong_candidate | replacement_failed_no_candidate |
| rds_on_150c | critical | wrong_candidate | blocked_by_ai_review |
| ciss | high | unit_error | downgraded_to_review |
| qg | critical | wrong_candidate | replaced_selected_candidate |
| rth_jc | high | missing | marked_missing |
| junction_temperature | critical | wrong_candidate | replaced_selected_candidate |

## Safety Compliance

✅ **NO values were fabricated** - All repairs use existing candidates

## Constraints Compliance

✅ This round did NOT modify Excel files
✅ This round did NOT modify pipeline core files (parser.py, value_parser.py, final_selector.py, excel_writer.py)
✅ This round did NOT re-run parser or value_parser
✅ This round did NOT fabricate new values
✅ All replacements used existing candidates from selected_params_debug.json

## Recommendation

⚠️ Some critical issues could not be fully resolved.
Manual review recommended for the following fields:
- module_type: wrong_candidate
