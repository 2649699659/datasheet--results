# Final Selector Audit (Step 6.1)

## 1. Overview

| Metric | Value |
|--------|-------|
| document_count | 1 |
| field_count | 30 |
| **total_final_candidate** | **5** |
| total_review_needed | 20 |
| total_blocked | 3 |
| total_missing | 2 |

## 2. Documents Summary

| document_id | file_name | pdf_stem | final_candidate | review_needed | blocked | missing |
|-------------|----------|---------|----------------|--------------|--------|--------|
| f384879d1200 | ASC300N1200ME3.pdf | unknown | 5 | 20 | 3 | 2 |

## 3. Per-document Selection

### Document: ASC300N1200ME3.pdf

document_id: `f384879d1200`  |  pdf_stem: `unknown`

#### Final Candidates
| Field ID | Value | Unit | Score | Page | Reason |
|----------|-------|------|-------|------|--------|
| rds_on_25c | typ=5.3, max=6.7 | mΩ | 88 | 1 | score=88 passes threshold, no dangerous blockers |
| vgs_th | min=2.0, max=4.0 |  | 58 | 2 | score=58 passes threshold, no dangerous blockers |
| trr | typ=96.0 | ns | 88 | 3 | score=88 passes threshold, no dangerous blockers |
| lstray | typ=20.0 | nH | 88 | 3 | score=88 passes threshold, no dangerous blockers |
| weight | typ=340.0 | g | 88 | 3 | score=88 passes threshold, no dangerous blockers |

#### Review Needed
| Field ID | Score | Reason | Warnings | Candidates |
|----------|-------|--------|----------|------------|
| eon | 70 | energy_field_unit_missing_or_wrong; eon_selected_r | candidate_row_only_value_not_parsed, unit_not_found, energy_ | 9 |
| rds_on_150c | 60 | rds_on_150c_missing_150c_temperature_condition | candidate_row_only_value_not_parsed, rds_on_150c_missing_150 | 5 |
| voltage_rating | -17 | high_risk_rating_field_review_first | candidate_row_only_value_not_parsed | 5 |
| current_rating | -17 | high_risk_rating_field_review_first | candidate_row_only_value_not_parsed | 10 |
| part_number | -37 | table_candidate_should_be_metadata_extraction | no_reliable_header, candidate_row_only_value_not_parsed | 2 |
| module_type | -37 | parse_status=unsafe not clean enough for final | no_reliable_header, candidate_row_only_value_not_parsed | 3 |
| crss | -37 | parse_status=unsafe not clean enough for final | no_reliable_header, candidate_row_only_value_not_parsed | 3 |
| qg | -37 | parse_status=unsafe not clean enough for final | no_reliable_header, candidate_row_only_value_not_parsed | 14 |
| qgd | -37 | parse_status=unsafe not clean enough for final | no_reliable_header, candidate_row_only_value_not_parsed | 5 |
| qrr | -37 | parse_status=unsafe not clean enough for final | no_reliable_header, candidate_row_only_value_not_parsed | 4 |
| irrm | -37 | parse_status=unsafe not clean enough for final | no_reliable_header, candidate_row_only_value_not_parsed | 2 |
| isol | -37 | parse_status=unsafe not clean enough for final | no_reliable_header, candidate_row_only_value_not_parsed | 2 |
| clearance_tt | -37 | parse_status=unsafe not clean enough for final | no_reliable_header, candidate_row_only_value_not_parsed | 2 |
| creepage_tt | -37 | parse_status=unsafe not clean enough for final | no_reliable_header, candidate_row_only_value_not_parsed | 2 |
| ciss | -42 | parse_status=unsafe not clean enough for final | no_reliable_header, candidate_row_only_value_not_parsed, uni | 3 |
| coss | -42 | parse_status=unsafe not clean enough for final | no_reliable_header, candidate_row_only_value_not_parsed, uni | 3 |
| qgs | -42 | parse_status=unsafe not clean enough for final | no_reliable_header, candidate_row_only_value_not_parsed, uni | 3 |
| junction_temperature | -42 | parse_status=unsafe not clean enough for final | no_reliable_header, candidate_row_only_value_not_parsed, uni | 10 |
| eoff | -117 | parse_status=unsafe not clean enough for final | no_reliable_header, candidate_row_only_value_not_parsed, uni | 5 |
| rth_jh | -117 | parse_status=unsafe not clean enough for final | no_reliable_header, candidate_row_only_value_not_parsed, uni | 2 |

#### Blocked
| Field ID | Reason | Candidates |
|----------|--------|------------|
| rth_jc | dangerous_blockers: no_value_parsed | 1 |
| clearance_tb | condition_type_mismatch_tt_vs_tb | 2 |
| creepage_tb | condition_type_mismatch_tt_vs_tb | 2 |

#### Missing
| Field ID | Suggested Action |
|----------|------------------|
| manufacturer | metadata/page_text extraction |
| err | parser_fix_or_missing_in_pdf |

## 4. vgs_th Selection Check

**Document**: ASC300N1200ME3.pdf (`f384879d1200`)
**Selection Status**: final_candidate
**Selector Score**: 58
**Selector Reason**: score=58 passes threshold, no dangerous blockers

| Property | Value |
|----------|-------|
| min | 2.0 |
| max | 4.0 |
| value | None |
| original_unit |  |
| source_page | 2 |
| source_text | VGS(th) Gate Threshold Voltage 2 - 4 V VDS=VGS; ID=30mA |
| parse_status | partial |
| parse_quality | high |
| unit_sanity_status | ok |

**Is Clean vgs_th (min=2.0, max=4.0, unit=V, no figure)**: NO ❌

## 5. High-risk Rating Fields

### current_rating

**Document**: ASC300N1200ME3.pdf (`f384879d1200`)
- Selection Status: review_needed
- Selector Score: -17
- Selector Reason: high_risk_rating_field_review_first
- Best Candidate: value=300.0, unit=A
- Candidate Count: 10
- Why not in Final: High-risk field. Defaulted to review_needed per v1 rules.

### voltage_rating

**Document**: ASC300N1200ME3.pdf (`f384879d1200`)
- Selection Status: review_needed
- Selector Score: -17
- Selector Reason: high_risk_rating_field_review_first
- Best Candidate: value=1200.0, unit=V
- Candidate Count: 5
- Why not in Final: High-risk field. Defaulted to review_needed per v1 rules.
