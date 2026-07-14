# Final Selector Audit (Step 6.1)

## 1. Overview

| Metric | Value |
|--------|-------|
| document_count | 1 |
| field_count | 30 |
| **total_final_candidate** | **5** |
| total_review_needed | 21 |
| total_blocked | 2 |
| total_missing | 2 |

## 2. Documents Summary

| document_id | file_name | pdf_stem | final_candidate | review_needed | blocked | missing |
|-------------|----------|---------|----------------|--------------|--------|--------|
| 0f697ce5631f2ab4 | ASC300N1200ME3.pdf | ASC300N1200ME3 | 5 | 21 | 2 | 2 |

## 3. Per-document Selection

### Document: ASC300N1200ME3.pdf

document_id: `0f697ce5631f2ab4`  |  pdf_stem: `ASC300N1200ME3`

#### Final Candidates
| Field ID | Value | Unit | Score | Page | Reason |
|----------|-------|------|-------|------|--------|
| rds_on_25c | typ=5.3, max=6.7 | mΩ | 88 | 1 | score=88 passes threshold, no dangerous blockers |
| vgs_th | min=2.0, max=4.0 | V | 63 | 2 | score=63 passes threshold, no dangerous blockers |
| trr | typ=96.0 | ns | 88 | 3 | score=88 passes threshold, no dangerous blockers |
| lstray | typ=20.0 | nH | 88 | 3 | score=88 passes threshold, no dangerous blockers |
| weight | typ=340.0 | g | 88 | 3 | score=88 passes threshold, no dangerous blockers |

#### Review Needed
| Field ID | Score | Reason | Warnings | Candidates |
|----------|-------|--------|----------|------------|
| voltage_rating | 78 | high_risk_rating_field_review_first | candidate_row_only_value_not_parsed | 11 |
| eon | 70 | energy_field_unit_missing_or_wrong; eon_selected_r | candidate_row_only_value_not_parsed, unit_not_found, energy_ | 5 |
| junction_temperature | 65 | junction_temperature_from_figure_axis_not_table_ro | candidate_row_only_value_not_parsed, unit_not_found, junctio | 6 |
| rds_on_150c | 60 | rds_on_150c_missing_150c_temperature_condition | candidate_row_only_value_not_parsed, rds_on_150c_missing_150 | 3 |
| current_rating | -17 | high_risk_rating_field_review_first | candidate_row_only_value_not_parsed | 10 |
| part_number | -37 | table_candidate_should_be_metadata_extraction | no_reliable_header, candidate_row_only_value_not_parsed | 1 |
| module_type | -37 | parse_status=unsafe not clean enough for final | no_reliable_header, candidate_row_only_value_not_parsed | 1 |
| crss | -37 | parse_status=unsafe not clean enough for final | no_reliable_header, candidate_row_only_value_not_parsed | 3 |
| qrr | -37 | parse_status=unsafe not clean enough for final | no_reliable_header, candidate_row_only_value_not_parsed | 2 |
| irrm | -37 | parse_status=unsafe not clean enough for final | no_reliable_header, candidate_row_only_value_not_parsed | 1 |
| isol | -37 | parse_status=unsafe not clean enough for final | no_reliable_header, candidate_row_only_value_not_parsed | 1 |
| clearance_tt | -37 | parse_status=unsafe not clean enough for final | no_reliable_header, candidate_row_only_value_not_parsed | 1 |
| creepage_tt | -37 | parse_status=unsafe not clean enough for final | no_reliable_header, candidate_row_only_value_not_parsed | 1 |
| ciss | -42 | parse_status=unsafe not clean enough for final | no_reliable_header, candidate_row_only_value_not_parsed, uni | 2 |
| qg | -42 | parse_status=unsafe not clean enough for final | no_reliable_header, candidate_row_only_value_not_parsed, uni | 8 |
| qgd | -42 | parse_status=unsafe not clean enough for final | no_reliable_header, candidate_row_only_value_not_parsed, uni | 2 |
| coss | -117 | parse_status=unsafe not clean enough for final | no_reliable_header, candidate_row_only_value_not_parsed, uni | 1 |
| qgs | -117 | parse_status=unsafe not clean enough for final | no_reliable_header, candidate_row_only_value_not_parsed, uni | 1 |
| eoff | -117 | parse_status=unsafe not clean enough for final | no_reliable_header, candidate_row_only_value_not_parsed, uni | 3 |
| err | -117 | parse_status=unsafe not clean enough for final | no_reliable_header, candidate_row_only_value_not_parsed, uni | 2 |
| rth_jh | -117 | parse_status=unsafe not clean enough for final | no_reliable_header, candidate_row_only_value_not_parsed, uni | 1 |

#### Blocked
| Field ID | Reason | Candidates |
|----------|--------|------------|
| clearance_tb | condition_type_mismatch_tt_vs_tb | 1 |
| creepage_tb | condition_type_mismatch_tt_vs_tb | 1 |

#### Missing
| Field ID | Suggested Action |
|----------|------------------|
| manufacturer | metadata/page_text extraction |
| rth_jc | parser_fix_or_missing_in_pdf |

## 4. vgs_th Selection Check

**Document**: ASC300N1200ME3.pdf (`0f697ce5631f2ab4`)
**Selection Status**: final_candidate
**Selector Score**: 63
**Selector Reason**: score=63 passes threshold, no dangerous blockers

| Property | Value |
|----------|-------|
| min | 2.0 |
| max | 4.0 |
| value | None |
| original_unit | V |
| source_page | 2 |
| source_text | V GS(th) Gate Threshold Voltage 2 - 4 V V =V ; I =30mA DS GS D |
| parse_status | partial |
| parse_quality | high |
| unit_sanity_status | ok |

**Is Clean vgs_th (min=2.0, max=4.0, unit=V, no figure)**: YES ✅

## 5. High-risk Rating Fields

### current_rating

**Document**: ASC300N1200ME3.pdf (`0f697ce5631f2ab4`)
- Selection Status: review_needed
- Selector Score: -17
- Selector Reason: high_risk_rating_field_review_first
- Best Candidate: value=25.0, unit=A
- Candidate Count: 10
- Why not in Final: High-risk field. Defaulted to review_needed per v1 rules.

### voltage_rating

**Document**: ASC300N1200ME3.pdf (`0f697ce5631f2ab4`)
- Selection Status: review_needed
- Selector Score: 78
- Selector Reason: high_risk_rating_field_review_first
- Best Candidate: unit=V
- Candidate Count: 11
- Why not in Final: High-risk field. Defaulted to review_needed per v1 rules.
