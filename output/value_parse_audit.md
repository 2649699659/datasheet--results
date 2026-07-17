# Value Parse Audit (Step 5.9)

## 0. Field ID Validation

| Metric | Value |
|--------|-------|
| Total unique field_ids | 28 |
| Invalid field_ids | 0 |
| Missing from parsed | 2 |
| Missing IDs list | err, manufacturer |
| Validation status | **WARN (some target fields not in parsed)** |

## 1. Overview

| Metric | Value |
|--------|-------|
| Active Candidates | 116 |
| Parsed Value Count | 98 |
| Failed Parse Count | 18 |
| Fields with Values | 27 |
| Fields without Values | 1 |

## 1.5. Parse Quality Breakdown

| Metric | Count |
|--------|-------|
| parse_status=parsed | 95 |
| parse_status=partial | 3 |
| parse_status=unsafe | 0 |
| parse_status=failed | 18 |
| parse_quality=high | 113 |
| parse_quality=medium | 1 |
| parse_quality=low | 2 |
| unit_mismatch | 0 |

## 1.6. Unit Mismatch Summary

*No unit mismatches found.*

## 1.7. Ambiguous Numeric Columns

| Field ID | Page | Table | Row | Issue |
|----------|------|-------|-----|-------|
| current_rating | 1 | 1 | 3 | candidate_row_only_value_not_parsed; ambiguous_rating_row |
| current_rating | 2 | 1 | 3 | candidate_row_only_value_not_parsed; possible_test_condition_value; ambiguous_rating_row |
| current_rating | 2 | 4 | 3 | candidate_row_only_value_not_parsed; possible_test_condition_value; ambiguous_rating_row |

## 2. Parse Success by Field

| Field ID | Cand | Parsed | Failed | parse_status | Units Found | Issues |
|----------|------|--------|--------|--------------|-------------|--------|
| qg | 14 | 13 | 1 | failed,parsed | nC | candidate_row_only_value_not_parsed, no_reliable_header |
| current_rating | 10 | 9 | 1 | failed,parsed,partial | A, μA | ambiguous_rating_row, candidate_row_only_value_not_parsed, n |
| junction_temperature | 10 | 6 | 4 | failed,parsed | - | candidate_row_only_value_not_parsed, figure_caption_not_para |
| eon | 9 | 7 | 2 | failed,parsed | - | candidate_row_only_value_not_parsed, no_reliable_header |
| voltage_rating | 5 | 4 | 1 | failed,parsed | V | candidate_row_only_value_not_parsed |
| rds_on_25c | 5 | 5 | 0 | parsed | mΩ | candidate_row_only_value_not_parsed, no_reliable_header |
| rds_on_150c | 5 | 5 | 0 | parsed | mΩ | candidate_row_only_value_not_parsed, no_reliable_header |
| qgd | 5 | 5 | 0 | parsed | nC | candidate_row_only_value_not_parsed, no_reliable_header |
| eoff | 5 | 3 | 2 | failed,parsed | - | candidate_row_only_value_not_parsed, no_reliable_header |
| trr | 5 | 5 | 0 | parsed | ns | candidate_row_only_value_not_parsed, no_reliable_header |
| qrr | 4 | 4 | 0 | parsed | nC | candidate_row_only_value_not_parsed, no_reliable_header |
| module_type | 3 | 2 | 1 | failed,parsed | ns | candidate_row_only_value_not_parsed, no_reliable_header |
| vgs_th | 3 | 3 | 0 | parsed | V | candidate_row_only_value_not_parsed, no_reliable_header, par |
| ciss | 3 | 2 | 1 | failed,parsed | - | candidate_row_only_value_not_parsed, no_reliable_header |
| coss | 3 | 3 | 0 | parsed | - | candidate_row_only_value_not_parsed, no_reliable_header |
| crss | 3 | 3 | 0 | parsed | pF | candidate_row_only_value_not_parsed, no_reliable_header |
| qgs | 3 | 3 | 0 | parsed | - | candidate_row_only_value_not_parsed, no_reliable_header |
| part_number | 2 | 2 | 0 | parsed | - | candidate_row_only_value_not_parsed, no_reliable_header |
| rth_jh | 2 | 2 | 0 | parsed | - | candidate_row_only_value_not_parsed, no_reliable_header |
| irrm | 2 | 2 | 0 | parsed | A | candidate_row_only_value_not_parsed, no_reliable_header |
| lstray | 2 | 2 | 0 | parsed | nH | candidate_row_only_value_not_parsed |
| weight | 2 | 2 | 0 | parsed | g | candidate_row_only_value_not_parsed |
| isol | 2 | 2 | 0 | parsed | kV | candidate_row_only_value_not_parsed, no_reliable_header |
| clearance_tt | 2 | 1 | 1 | failed,parsed | mm | candidate_row_only_value_not_parsed, condition_unclear, cond |
| clearance_tb | 2 | 1 | 1 | failed,parsed | mm | condition_type_mismatch: expected t_b, got t_t, condition_ty |
| creepage_tt | 2 | 1 | 1 | failed,parsed | mm | candidate_row_only_value_not_parsed, condition_unclear, cond |
| creepage_tb | 2 | 1 | 1 | failed,parsed | mm | condition_type_mismatch: expected t_b, got t_t, condition_ty |
| rth_jc | 1 | 0 | 1 | failed | - | candidate_row_only_value_not_parsed |

## 3. High-risk Rating Fields

### current_rating

Total: 10 candidates
**Possible test condition values**: 2
**Ambiguous rows**: 3

**Page 1, Table 1, Row 3**
- Values: value=300.0
- Unit: A / normalized: A
- Condition: TC=25
- Review: candidate_row_only_value_not_parsed; ambiguous_rating_row

**Page 1, Table 2, Row 5**
- Values: NO VALUE
- Unit: A / normalized: A
- Condition: (no condition)
- Review: candidate_row_only_value_not_parsed; no_value_parsed

**Page 2, Table 0, Row 3**
- Values: value=300.0
- Unit: A / normalized: A
- Condition: TC=25
- Review: candidate_row_only_value_not_parsed

### voltage_rating

Total: 5 candidates

**Page 1, Table 1, Row 2**
- Values: value=1200.0
- Unit: V / normalized: V
- Condition: TC=25
- Review: candidate_row_only_value_not_parsed

**Page 1, Table 2, Row 3**
- Values: value=1200.0
- Unit: V / normalized: V
- Condition: TC=25
- Review: candidate_row_only_value_not_parsed

**Page 2, Table 0, Row 1**
- Values: value=1200.0
- Unit: V / normalized: V
- Condition: (no condition)
- Review: candidate_row_only_value_not_parsed

## 4. VGS(th) Check

Total: 3 candidates

| Page | Table | min | max | value | Unit | unit_source | parse_status | parse_quality | Review |
|------|-------|-----|-----|-------|------|-------------|--------------|-------|
| 2 | 5 | 2.0 | 4.0 | - |  | source_text_fallback | partial | high | candidate_row_only_value_not_parsed; unit_not_found |
| 2 | 5 | 2.0 | 4.0 | - |  | source_text_fallback | partial | high | candidate_row_only_value_not_parsed; unit_not_found |
| 4 | 8 | - | - | 300.0 | V | source_text_fallback | unsafe | low | candidate_row_only_value_not_parsed; no_reliable_header; par |

**Details with source_text and range info (Step 5.9):**

**Page 2, Row 5**: "VGS(th) Gate Threshold Voltage 2 - 4 V VDS=VGS; ID=30mA"
- min=2.0, max=4.0, value=None
- unit=, unit_source=source_text_fallback, unit_warning=unit_from_source_text_but_is_condition_rejected
- numeric_tokens_detected=[2.0, 4.0]
- value_source_columns=['range_from_split_cells']
- condition=
- review_reason=candidate_row_only_value_not_parsed; unit_not_found

**Page 2, Row 5**: "VGS(th) Gate Threshold Voltage 2 - 4 V VDS=VGS; ID=30mA"
- min=2.0, max=4.0, value=None
- unit=, unit_source=source_text_fallback, unit_warning=unit_from_source_text_but_is_condition_rejected
- numeric_tokens_detected=[2.0, 4.0]
- value_source_columns=['range_from_split_cells']
- condition=
- review_reason=candidate_row_only_value_not_parsed; unit_not_found

**Page 4, Row 8**: "Threshold Voltage, Vth(V) 300"
- min=None, max=None, value=300.0
- unit=V, unit_source=source_text_fallback, unit_warning=unit_from_source_text_fallback
- numeric_tokens_detected=[300.0]
- value_source_columns=['source_text_fallback']
- condition=
- review_reason=candidate_row_only_value_not_parsed; no_reliable_header; partial_threshold_values

## 5. Example Values by Field

### qg

**Page 1, Row 10**: value=618.0
- Unit: - | Condition: TC=25; ID=150A
- Source: "QG Total Gate Charge - 618 - nC VDD=800V; VGS=-5/+18V; ID=150A; TC=25C"
- Review: candidate_row_only_value_not_parsed; no_reliable_header; unit_not_found

**Page 1, Row 11**: value=147.0
- Unit: - | Condition: -
- Source: "QGD Gate-Drain Charge - 147 -"
- Review: candidate_row_only_value_not_parsed; no_reliable_header; unit_not_found

### current_rating

**Page 1, Row 3**: value=300.0
- Unit: A | Condition: TC=25
- Source: "ID Drain Current (continuous) 300 A TC=25C"
- Review: candidate_row_only_value_not_parsed; ambiguous_rating_row

**Page 1, Row 5**: NO VALUE
- Unit: A | Condition: -
- Source: "ID Drain Current (continuous) A"
- Review: candidate_row_only_value_not_parsed; no_value_parsed

### junction_temperature

**Page 1, Row 5**: value=175.0
- Unit: - | Condition: -
- Source: "TJ; MAX Junction Temperature 175 C"
- Review: candidate_row_only_value_not_parsed; no_reliable_header; unit_not_found

**Page 1, Row 13**: value=1839.0
- Unit: - | Condition: TJ=25
- Source: "QRR Reverse Recovery Charge - 1839 - nC VGS=-5/+18V; IF=150A; VR=800V; RG(ext)=5Ω; Load=50µH; TJ=25C"
- Review: candidate_row_only_value_not_parsed; no_reliable_header; unit_not_found

### eon

**Page 1, Row 8**: typ=5.3, max=6.7
- Unit: - | Condition: TC=25; ID=150A; VGS=18V
- Source: "RDS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ VGS=18V; ID=150A; TC=25C"
- Review: candidate_row_only_value_not_parsed; unit_not_found

**Page 1, Row 10**: typ=5.3, max=6.7
- Unit: - | Condition: TC=25; ID=150A; VGS=18V
- Source: "RDS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ VGS=18V; ID=150A; TC=25C"
- Review: candidate_row_only_value_not_parsed; unit_not_found

### voltage_rating

**Page 1, Row 2**: value=1200.0
- Unit: V | Condition: TC=25
- Source: "VDS Drain-Source Voltage 1200 V TC=25C"
- Review: candidate_row_only_value_not_parsed

**Page 1, Row 3**: value=1200.0
- Unit: V | Condition: TC=25
- Source: "VDS Drain-Source Voltage 1200 V TC=25C"
- Review: candidate_row_only_value_not_parsed

### rds_on_25c

**Page 1, Row 8**: typ=5.3, max=6.7
- Unit: mΩ | Condition: TC=25; ID=150A; VGS=18V
- Source: "RDS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ VGS=18V; ID=150A; TC=25C"
- Review: candidate_row_only_value_not_parsed

**Page 1, Row 10**: typ=5.3, max=6.7
- Unit: mΩ | Condition: TC=25; ID=150A; VGS=18V
- Source: "RDS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ VGS=18V; ID=150A; TC=25C"
- Review: candidate_row_only_value_not_parsed

### rds_on_150c

**Page 1, Row 8**: typ=5.3, max=6.7
- Unit: mΩ | Condition: TC=25; ID=150A; VGS=18V
- Source: "RDS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ VGS=18V; ID=150A; TC=25C"
- Review: candidate_row_only_value_not_parsed

**Page 1, Row 10**: typ=5.3, max=6.7
- Unit: mΩ | Condition: TC=25; ID=150A; VGS=18V
- Source: "RDS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ VGS=18V; ID=150A; TC=25C"
- Review: candidate_row_only_value_not_parsed

### qgd

**Page 1, Row 11**: value=147.0
- Unit: - | Condition: -
- Source: "QGD Gate-Drain Charge - 147 -"
- Review: candidate_row_only_value_not_parsed; no_reliable_header; unit_not_found

**Page 1, Row 16**: value=147.0
- Unit: - | Condition: -
- Source: "QGD Gate-Drain Charge - 147 -"
- Review: candidate_row_only_value_not_parsed; no_reliable_header; unit_not_found

### eoff

**Page 2, Row 15**: value=7.9
- Unit: - | Condition: -
- Source: "Eoff Turn-off Energy - 7.9 -"
- Review: candidate_row_only_value_not_parsed; no_reliable_header; unit_not_found

**Page 2, Row 2**: value=7.9
- Unit: - | Condition: -
- Source: "Eoff Turn-off Energy - 7.9 -"
- Review: candidate_row_only_value_not_parsed; no_reliable_header; unit_not_found

### trr

**Page 2, Row 20**: value=42.0
- Unit: - | Condition: -
- Source: "tr Rise Time - 42 -"
- Review: candidate_row_only_value_not_parsed; no_reliable_header; unit_not_found

**Page 2, Row 7**: value=42.0
- Unit: - | Condition: -
- Source: "tr Rise Time - 42 -"
- Review: candidate_row_only_value_not_parsed; no_reliable_header; unit_not_found

## 6. Unit Source Summary

| Unit Source | Count |
|-------------|-------|
| unit_column | 18 |
| value_cell | 0 |
| adjacent_cell | 0 |
| source_text_fallback | 40 |
| not_found | 22 |
| rejected_wrong_dimension | 36 |

**Wrong dimension rejected by field**: {'junction_temperature': 8, 'eon': 4, 'qg': 7, 'rth_jh': 2, 'coss': 2, 'eoff': 5, 'qgs': 2, 'ciss': 2, 'rds_on_25c': 1, 'rds_on_150c': 1, 'crss': 1, 'rth_jc': 1}

## 7. Condition Unit Exclusion Summary

| Metric | Count |
|--------|-------|
| Params with condition units rejected | 15 |
| Fields affected | 10 |
| Field list | ciss, coss, current_rating, eon, junction_temperature, qg, qgd, qgs, qrr, vgs_th |

## 8. Range Parsing Summary

*No range values detected.*

## 9. Slash-list Summary

*No slash-list values detected.*

## 10. Clearance/Creepage T-T/T-B Check

| Field ID | Count | Accepted TT | Accepted TB | Mismatch | Condition Unclear |
|----------|-------|-------------|-------------|----------|-------------------|
| clearance_tt | 2 | 1 | 0 | 0 | 1 |
| clearance_tb | 2 | 0 | 0 | 1 | 1 |
| creepage_tt | 2 | 1 | 0 | 0 | 1 |
| creepage_tb | 2 | 0 | 0 | 1 | 1 |

**Detail:**

### clearance_tt

- Page 3, Table 1, Row 5
  - Value: 11.0 mm
  - Condition: Terminal to Terminal
  - Review: candidate_row_only_value_not_parsed; no_reliable_header
  - Source: "- Clearance Distance - 11 - mm Terminal to Terminal"

- Page 3, Table 3, Row 7
  - Value: None 
  - Condition: (no condition)
  - Review: condition_unclear: clearance/creepage T-T unspecified; no_value_parsed; condition_unclear; unit_not_
  - Source: "- Clearance Distance"

### clearance_tb

- Page 3, Table 1, Row 5
  - Value: 11.0 mm
  - Condition: Terminal to Terminal
  - Review: condition_type_mismatch: field=_tb but row has T-T; no_reliable_header; condition_type_mismatch: exp
  - Source: "- Clearance Distance - 11 - mm Terminal to Terminal"

- Page 3, Table 3, Row 7
  - Value: None 
  - Condition: (no condition)
  - Review: condition_unclear: clearance/creepage T-B unspecified; no_value_parsed; condition_unclear; unit_not_
  - Source: "- Clearance Distance"

### creepage_tt

- Page 3, Table 1, Row 7
  - Value: 23.0 mm
  - Condition: Terminal to Terminal
  - Review: candidate_row_only_value_not_parsed; no_reliable_header
  - Source: "- Creepage Distance - 23 - mm Terminal to Terminal"

- Page 3, Table 3, Row 10
  - Value: None 
  - Condition: (no condition)
  - Review: condition_unclear: clearance/creepage T-T unspecified; no_value_parsed; condition_unclear; unit_not_
  - Source: "- Creepage Distance"

### creepage_tb

- Page 3, Table 1, Row 7
  - Value: 23.0 mm
  - Condition: Terminal to Terminal
  - Review: condition_type_mismatch: field=_tb but row has T-T; no_reliable_header; condition_type_mismatch: exp
  - Source: "- Creepage Distance - 23 - mm Terminal to Terminal"

- Page 3, Table 3, Row 10
  - Value: None 
  - Condition: (no condition)
  - Review: condition_unclear: clearance/creepage T-B unspecified; no_value_parsed; condition_unclear; unit_not_
  - Source: "- Creepage Distance"

## 11. Figure/Caption Rejection Summary (Step 5.9)

**Total rejected: 1**

| Field ID | Page | Row | source_text |
|----------|------|-----|-------------|
| junction_temperature | 3 | 0 | B ody Diode Characteristics (at TJ=25℃ unless otherwise specified) |

## 12. Wrong Dimension Unit Rejection Summary (Step 5.9)

| Metric | Count |
|--------|-------|
| Total wrong dimension rejected | 36 |

| Field ID | Count | Rejected Units |
|----------|-------|----------------|
| ciss | 2 | s |
| coss | 2 | s |
| crss | 1 | s |
| eoff | 5 | F, pF |
| eon | 4 | mΩ |
| junction_temperature | 8 | C, J, Ω |
| qg | 7 | V, g, s |
| qgs | 2 | s |
| rds_on_150c | 1 | A |
| rds_on_25c | 1 | A |
| rth_jc | 1 | F |
| rth_jh | 2 | C |

**Detail:**

### ciss

- Page 2, Row 12: unit_warning=rejected_wrong_dimension:s
  - source_text: "Ciss Input Capacitance - 9.15 -"
  - value=9.15, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 5, Row 5: unit_warning=rejected_wrong_dimension:s
  - source_text: "CISS"
  - value=None, unit_source=rejected_wrong_dimension:source_text_fallback

### coss

- Page 2, Row 12: unit_warning=rejected_wrong_dimension:s
  - source_text: "Coss Output Capacitance - 0.29 -"
  - value=0.29, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 5, Row 11: unit_warning=rejected_wrong_dimension:s
  - source_text: "COSS 10"
  - value=10.0, unit_source=rejected_wrong_dimension:source_text_fallback

### crss

- Page 5, Row 14: unit_warning=rejected_wrong_dimension:s
  - source_text: "CRSS 5"
  - value=5.0, unit_source=rejected_wrong_dimension:source_text_fallback

### eoff

- Page 2, Row 15: unit_warning=rejected_wrong_dimension:F
  - source_text: "Eoff Turn-off Energy - 7.9 -"
  - value=7.9, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 2, Row 2: unit_warning=rejected_wrong_dimension:F
  - source_text: "Eoff Turn-off Energy - 7.9 -"
  - value=7.9, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 2, Row 20: unit_warning=rejected_wrong_dimension:F
  - source_text: "Eoff Turn-off Energy - 7.9 -"
  - value=7.9, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 5, Row 3: unit_warning=rejected_wrong_dimension:F
  - source_text: "Eoff"
  - value=None, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 5, Row 10: unit_warning=rejected_wrong_dimension:pF
  - source_text: "Capacitance (pF) Switching Loss (mJ) Eoff"
  - value=None, unit_source=rejected_wrong_dimension:source_text_fallback

### eon

- Page 1, Row 8: unit_warning=rejected_wrong_dimension:mΩ
  - source_text: "RDS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ VGS=18V; ID=150A; TC=25C"
  - value=None, unit_source=rejected_wrong_dimension:unit_column

- Page 1, Row 10: unit_warning=rejected_wrong_dimension:mΩ
  - source_text: "RDS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ VGS=18V; ID=150A; TC=25C"
  - value=None, unit_source=rejected_wrong_dimension:unit_column

- Page 2, Row 6: unit_warning=rejected_wrong_dimension:mΩ
  - source_text: "RDS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ VGS=18V; ID=150A"
  - value=5.3, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 2, Row 6: unit_warning=rejected_wrong_dimension:mΩ
  - source_text: "RDS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ VGS=18V; ID=150A"
  - value=5.3, unit_source=rejected_wrong_dimension:source_text_fallback

### junction_temperature

- Page 1, Row 5: unit_warning=rejected_wrong_dimension:C
  - source_text: "TJ; MAX Junction Temperature 175 C"
  - value=175.0, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 1, Row 7: unit_warning=rejected_wrong_dimension:C
  - source_text: "TJ; MAX Junction Temperature 175 C"
  - value=175.0, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 1, Row 20: unit_warning=rejected_wrong_dimension:Ω
  - source_text: "RG(ext)=5Ω; Load=50µH; TJ=25C"
  - value=5.0, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 2, Row 7: unit_warning=rejected_wrong_dimension:C
  - source_text: "TJ; MAX Junction Temperature 175 C"
  - value=175.0, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 2, Row 9: unit_warning=rejected_wrong_dimension:C
  - source_text: "TJ; MAX Junction Temperature 175 C"
  - value=175.0, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 4, Row 7: unit_warning=rejected_wrong_dimension:J
  - source_text: "TJ=175℃"
  - value=None, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 4, Row 10: unit_warning=rejected_wrong_dimension:J
  - source_text: "TJ=25℃"
  - value=None, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 4, Row 13: unit_warning=rejected_wrong_dimension:J
  - source_text: "TJ=-55℃"
  - value=None, unit_source=rejected_wrong_dimension:source_text_fallback

### qg

- Page 1, Row 12: unit_warning=rejected_wrong_dimension:g
  - source_text: "QG Total Gate Charge - 618 -"
  - value=618.0, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 2, Row 18: unit_warning=rejected_wrong_dimension:g
  - source_text: "QG Total Gate Charge - 618 -"
  - value=618.0, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 2, Row 3: unit_warning=rejected_wrong_dimension:s
  - source_text: "QGS Gate-Source Charge - 174 -"
  - value=174.0, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 2, Row 5: unit_warning=rejected_wrong_dimension:g
  - source_text: "QG Total Gate Charge - 618 -"
  - value=618.0, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 2, Row 21: unit_warning=rejected_wrong_dimension:s
  - source_text: "QGS Gate-Source Charge - 174 -"
  - value=174.0, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 2, Row 23: unit_warning=rejected_wrong_dimension:g
  - source_text: "QG Total Gate Charge - 618 -"
  - value=618.0, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 5, Row 16: unit_warning=rejected_wrong_dimension:V
  - source_text: "Drain-Source Voltage, VDS (V) Gate Charge, QG (nC)"
  - value=None, unit_source=rejected_wrong_dimension:source_text_fallback

### qgs

- Page 2, Row 3: unit_warning=rejected_wrong_dimension:s
  - source_text: "QGS Gate-Source Charge - 174 -"
  - value=174.0, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 2, Row 21: unit_warning=rejected_wrong_dimension:s
  - source_text: "QGS Gate-Source Charge - 174 -"
  - value=174.0, unit_source=rejected_wrong_dimension:source_text_fallback

### rds_on_150c

- Page 4, Row 9: unit_warning=rejected_wrong_dimension:A
  - source_text: "Drain-Source Current, IDS(A) 300 On Resistance, RDS(on) 1"
  - value=300.0, unit_source=rejected_wrong_dimension:source_text_fallback

### rds_on_25c

- Page 4, Row 9: unit_warning=rejected_wrong_dimension:A
  - source_text: "Drain-Source Current, IDS(A) 300 On Resistance, RDS(on) 1"
  - value=300.0, unit_source=rejected_wrong_dimension:source_text_fallback

### rth_jc

- Page 8, Row 13: unit_warning=rejected_wrong_dimension:F
  - source_text: "customer’s technical departments to evaluate the suitability of the product for the intended application and the"
  - value=None, unit_source=rejected_wrong_dimension:source_text_fallback

### rth_jh

- Page 2, Row 8: unit_warning=rejected_wrong_dimension:C
  - source_text: "Rth Jh Thermal Resistance, Junction-to-Heatsink 0.12 C/W"
  - value=0.12, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 2, Row 10: unit_warning=rejected_wrong_dimension:C
  - source_text: "Rth Jh Thermal Resistance, Junction-to-Heatsink 0.12 C/W"
  - value=0.12, unit_source=rejected_wrong_dimension:source_text_fallback
