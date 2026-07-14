# Value Parse Audit (Step 5.9)

## 0. Field ID Validation

| Metric | Value |
|--------|-------|
| Total unique field_ids | 28 |
| Invalid field_ids | 0 |
| Missing from parsed | 2 |
| Missing IDs list | manufacturer, rth_jc |
| Validation status | **WARN (some target fields not in parsed)** |

## 1. Overview

| Metric | Value |
|--------|-------|
| Active Candidates | 77 |
| Parsed Value Count | 66 |
| Failed Parse Count | 11 |
| Fields with Values | 28 |
| Fields without Values | 0 |

## 1.5. Parse Quality Breakdown

| Metric | Count |
|--------|-------|
| parse_status=parsed | 62 |
| parse_status=partial | 4 |
| parse_status=unsafe | 0 |
| parse_status=failed | 11 |
| parse_quality=high | 77 |
| parse_quality=medium | 0 |
| parse_quality=low | 0 |
| unit_mismatch | 0 |

## 1.6. Unit Mismatch Summary

*No unit mismatches found.*

## 1.7. Ambiguous Numeric Columns

| Field ID | Page | Table | Row | Issue |
|----------|------|-------|-----|-------|
| current_rating | 1 | 2 | 3 | candidate_row_only_value_not_parsed; ambiguous_rating_row |
| current_rating | 1 | 2 | 8 | candidate_row_only_value_not_parsed; ambiguous_rating_row; unit_not_found |
| current_rating | 2 | 2 | 3 | candidate_row_only_value_not_parsed; ambiguous_rating_row |
| current_rating | 2 | 2 | 6 | candidate_row_only_value_not_parsed; no_reliable_header; ambiguous_rating_row; unit_not_found |

## 2. Parse Success by Field

| Field ID | Cand | Parsed | Failed | parse_status | Units Found | Issues |
|----------|------|--------|--------|--------------|-------------|--------|
| voltage_rating | 11 | 10 | 1 | failed,parsed | V | candidate_row_only_value_not_parsed, figure_caption_not_para |
| current_rating | 10 | 8 | 2 | failed,parsed,partial | A, μA | ambiguous_rating_row, candidate_row_only_value_not_parsed, f |
| qg | 8 | 7 | 1 | failed,parsed | - | candidate_row_only_value_not_parsed, figure_caption_not_para |
| junction_temperature | 6 | 6 | 0 | parsed | - | candidate_row_only_value_not_parsed, no_reliable_header |
| eon | 5 | 4 | 1 | failed,parsed | - | candidate_row_only_value_not_parsed, no_reliable_header |
| rds_on_25c | 3 | 2 | 1 | failed,parsed | mΩ | candidate_row_only_value_not_parsed, figure_caption_not_para |
| rds_on_150c | 3 | 2 | 1 | failed,parsed | mΩ | candidate_row_only_value_not_parsed, figure_caption_not_para |
| crss | 3 | 2 | 1 | failed,parsed | pF | candidate_row_only_value_not_parsed, no_reliable_header |
| eoff | 3 | 2 | 1 | failed,parsed | - | candidate_row_only_value_not_parsed, no_reliable_header |
| qgd | 2 | 2 | 0 | parsed | - | candidate_row_only_value_not_parsed, no_reliable_header |
| qrr | 2 | 2 | 0 | parsed | nC | candidate_row_only_value_not_parsed, no_reliable_header |
| vgs_th | 2 | 1 | 1 | failed,parsed | V | candidate_row_only_value_not_parsed, figure_caption_not_para |
| ciss | 2 | 1 | 1 | failed,parsed | - | candidate_row_only_value_not_parsed, no_reliable_header |
| trr | 2 | 2 | 0 | parsed | ns | candidate_row_only_value_not_parsed, no_reliable_header |
| err | 2 | 2 | 0 | parsed | - | candidate_row_only_value_not_parsed, no_reliable_header, ran |
| part_number | 1 | 1 | 0 | parsed | - | candidate_row_only_value_not_parsed, no_reliable_header |
| module_type | 1 | 1 | 0 | parsed | - | candidate_row_only_value_not_parsed, no_reliable_header |
| rth_jh | 1 | 1 | 0 | parsed | - | candidate_row_only_value_not_parsed, no_reliable_header |
| coss | 1 | 1 | 0 | parsed | - | candidate_row_only_value_not_parsed, no_reliable_header |
| qgs | 1 | 1 | 0 | parsed | - | candidate_row_only_value_not_parsed, no_reliable_header |
| irrm | 1 | 1 | 0 | parsed | A | candidate_row_only_value_not_parsed, no_reliable_header |
| lstray | 1 | 1 | 0 | parsed | nH | candidate_row_only_value_not_parsed |
| weight | 1 | 1 | 0 | parsed | g | candidate_row_only_value_not_parsed |
| isol | 1 | 1 | 0 | parsed | kV | candidate_row_only_value_not_parsed, no_reliable_header |
| clearance_tt | 1 | 1 | 0 | parsed | mm | candidate_row_only_value_not_parsed, no_reliable_header |
| clearance_tb | 1 | 1 | 0 | parsed | mm | condition_type_mismatch: expected t_b, got t_t, condition_ty |
| creepage_tt | 1 | 1 | 0 | parsed | mm | candidate_row_only_value_not_parsed, no_reliable_header |
| creepage_tb | 1 | 1 | 0 | parsed | mm | condition_type_mismatch: expected t_b, got t_t, condition_ty |

## 3. High-risk Rating Fields

### current_rating

Total: 10 candidates
**Ambiguous rows**: 4

**Page 1, Table 2, Row 3**
- Values: value=300.0
- Unit: A / normalized: A
- Condition: (no condition)
- Review: candidate_row_only_value_not_parsed; ambiguous_rating_row

**Page 1, Table 2, Row 8**
- Values: typ=5.3, max=6.7
- Unit: normalized: A
- Condition: (no condition)
- Review: candidate_row_only_value_not_parsed; ambiguous_rating_row; unit_not_found

**Page 2, Table 1, Row 3**
- Values: value=25.0
- Unit: A / normalized: A
- Condition: (no condition)
- Review: candidate_row_only_value_not_parsed

### voltage_rating

Total: 11 candidates

**Page 1, Table 2, Row 2**
- Values: value=1200.0
- Unit: V / normalized: V
- Condition: (no condition)
- Review: candidate_row_only_value_not_parsed

**Page 2, Table 1, Row 1**
- Values: value=1200.0
- Unit: V / normalized: V
- Condition: (no condition)
- Review: candidate_row_only_value_not_parsed

**Page 2, Table 2, Row 2**
- Values: min=1200.0
- Unit: V / normalized: V
- Condition: (no condition)
- Review: candidate_row_only_value_not_parsed

## 4. VGS(th) Check

Total: 2 candidates

| Page | Table | min | max | value | Unit | unit_source | parse_status | parse_quality | Review |
|------|-------|-----|-----|-------|------|-------------|--------------|-------|
| 2 | 5 | 2.0 | 4.0 | - | V | source_text_fallback | partial | high | candidate_row_only_value_not_parsed |
| 4 | 1 | - | - | - |  | not_found | failed | low | figure_caption_not_parameter_row |

**Details with source_text and range info (Step 5.9):**

**Page 2, Row 5**: "V GS(th) Gate Threshold Voltage 2 - 4 V V =V ; I =30mA DS GS D"
- min=2.0, max=4.0, value=None
- unit=V, unit_source=source_text_fallback, unit_warning=unit_from_source_text_fallback
- numeric_tokens_detected=[2.0, 4.0]
- value_source_columns=['range_from_split_cells']
- condition=
- review_reason=candidate_row_only_value_not_parsed

**Page 4, Row 1**: "Figure 3 Threshold Voltage vs. Temperature"
- min=None, max=None, value=None
- unit=, unit_source=not_found, unit_warning=figure_caption_rejected
- numeric_tokens_detected=[]
- value_source_columns=[]
- condition=
- review_reason=figure_caption_not_parameter_row

## 5. Example Values by Field

### voltage_rating

**Page 1, Row 2**: value=1200.0
- Unit: V | Condition: -
- Source: "V DS Drain-Source Voltage 1200 V T =25C C"
- Review: candidate_row_only_value_not_parsed

**Page 2, Row 1**: value=1200.0
- Unit: V | Condition: -
- Source: "V DS Drain-Source Voltage 1200 V"
- Review: candidate_row_only_value_not_parsed

### current_rating

**Page 1, Row 3**: value=300.0
- Unit: A | Condition: -
- Source: "I D Drain Current (continuous) 300 A T =25C C"
- Review: candidate_row_only_value_not_parsed; ambiguous_rating_row

**Page 1, Row 8**: typ=5.3, max=6.7
- Unit: - | Condition: -
- Source: "R DS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ V =18V; I =150A; T =25C GS D C"
- Review: candidate_row_only_value_not_parsed; ambiguous_rating_row; unit_not_found

### qg

**Page 1, Row 10**: value=618.0
- Unit: - | Condition: -
- Source: "Q G Total Gate Charge - 618 - nC V =800V; V =-5/+18V; I =150A; DD GS D T =25C C"
- Review: candidate_row_only_value_not_parsed; no_reliable_header; unit_not_found

**Page 1, Row 11**: value=147.0
- Unit: - | Condition: -
- Source: "Q GD Gate-Drain Charge - 147 -"
- Review: candidate_row_only_value_not_parsed; no_reliable_header; unit_not_found

### junction_temperature

**Page 1, Row 5**: value=175.0
- Unit: - | Condition: -
- Source: "T J; MAX Junction Temperature 175 C"
- Review: candidate_row_only_value_not_parsed; no_reliable_header; unit_not_found

**Page 1, Row 13**: value=1839.0
- Unit: - | Condition: -
- Source: "Q RR Reverse Recovery Charge - 1839 - nC V =-5/+18V; I =150A; V =800V; GS F R R =5Ω; Load=50µH; T=25C G(ext) J"
- Review: candidate_row_only_value_not_parsed; no_reliable_header; unit_not_found

### eon

**Page 1, Row 8**: typ=5.3, max=6.7
- Unit: - | Condition: -
- Source: "R DS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ V =18V; I =150A; T =25C GS D C"
- Review: candidate_row_only_value_not_parsed; unit_not_found

**Page 2, Row 6**: value=5.3
- Unit: - | Condition: -
- Source: "R DS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ V =18V; I =150A GS D"
- Review: candidate_row_only_value_not_parsed; no_reliable_header; unit_not_found

### rds_on_25c

**Page 1, Row 8**: typ=5.3, max=6.7
- Unit: mΩ | Condition: -
- Source: "R DS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ V =18V; I =150A; T =25C GS D C"
- Review: candidate_row_only_value_not_parsed

**Page 2, Row 6**: value=5.3
- Unit: mΩ | Condition: -
- Source: "R DS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ V =18V; I =150A GS D"
- Review: candidate_row_only_value_not_parsed; no_reliable_header

### rds_on_150c

**Page 1, Row 8**: typ=5.3, max=6.7
- Unit: mΩ | Condition: -
- Source: "R DS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ V =18V; I =150A; T =25C GS D C"
- Review: candidate_row_only_value_not_parsed

**Page 2, Row 6**: value=5.3
- Unit: mΩ | Condition: -
- Source: "R DS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ V =18V; I =150A GS D"
- Review: candidate_row_only_value_not_parsed; no_reliable_header

### crss

**Page 2, Row 13**: value=45.0
- Unit: pF | Condition: -
- Source: "C rss Reverse Transfer Capacitance - 45 - pF"
- Review: candidate_row_only_value_not_parsed; no_reliable_header

**Page 5, Row 0**: value=100000.0
- Unit: - | Condition: -
- Source: "100000 C 10000 ISS )F p ( e1000 c n a tic C a OSS p a C 100 C RSS 10 0 200 400 600 800 1000 1200 Drain-Source Voltage, V..."
- Review: candidate_row_only_value_not_parsed; no_reliable_header; unit_not_found

### eoff

**Page 2, Row 15**: value=7.9
- Unit: - | Condition: -
- Source: "E off Turn-off Energy - 7.9 -"
- Review: candidate_row_only_value_not_parsed; no_reliable_header; unit_not_found

**Page 5, Row 0**: value=25.0
- Unit: - | Condition: -
- Source: "25 V =-5/+18V GS V =800V DS L=100μH 20 R G(ext) =5Ω E total )Jm 15 ( s so L g E off n ih 10 c tiw S E on 5 0 0 40 80 120..."
- Review: candidate_row_only_value_not_parsed; no_reliable_header; unit_not_found

### qgd

**Page 1, Row 11**: value=147.0
- Unit: - | Condition: -
- Source: "Q GD Gate-Drain Charge - 147 -"
- Review: candidate_row_only_value_not_parsed; no_reliable_header; unit_not_found

**Page 2, Row 17**: value=147.0
- Unit: - | Condition: -
- Source: "Q GD Gate-Drain Charge - 147 -"
- Review: candidate_row_only_value_not_parsed; no_reliable_header; unit_not_found

## 6. Unit Source Summary

| Unit Source | Count |
|-------------|-------|
| unit_column | 11 |
| value_cell | 0 |
| adjacent_cell | 0 |
| source_text_fallback | 18 |
| not_found | 15 |
| rejected_wrong_dimension | 33 |

**Wrong dimension rejected by field**: {'junction_temperature': 6, 'current_rating': 4, 'eon': 4, 'qg': 5, 'qrr': 1, 'rth_jh': 1, 'coss': 1, 'eoff': 3, 'qgs': 1, 'err': 2, 'crss': 2, 'voltage_rating': 2, 'ciss': 1}

## 7. Condition Unit Exclusion Summary

| Metric | Count |
|--------|-------|
| Params with condition units rejected | 2 |
| Fields affected | 2 |
| Field list | ciss, voltage_rating |

## 8. Range Parsing Summary

*No range values detected.*

## 9. Slash-list Summary

*No slash-list values detected.*

## 10. Clearance/Creepage T-T/T-B Check

| Field ID | Count | Accepted TT | Accepted TB | Mismatch | Condition Unclear |
|----------|-------|-------------|-------------|----------|-------------------|
| clearance_tt | 1 | 1 | 0 | 0 | 0 |
| clearance_tb | 1 | 0 | 0 | 1 | 0 |
| creepage_tt | 1 | 1 | 0 | 0 | 0 |
| creepage_tb | 1 | 0 | 0 | 1 | 0 |

**Detail:**

### clearance_tt

- Page 3, Table 2, Row 5
  - Value: 11.0 mm
  - Condition: Terminal to Terminal
  - Review: candidate_row_only_value_not_parsed; no_reliable_header
  - Source: "- Clearance Distance - 11 - mm Terminal to Terminal"

### clearance_tb

- Page 3, Table 2, Row 5
  - Value: 11.0 mm
  - Condition: Terminal to Terminal
  - Review: condition_type_mismatch: field=_tb but row has T-T; no_reliable_header; condition_type_mismatch: exp
  - Source: "- Clearance Distance - 11 - mm Terminal to Terminal"

### creepage_tt

- Page 3, Table 2, Row 7
  - Value: 23.0 mm
  - Condition: Terminal to Terminal
  - Review: candidate_row_only_value_not_parsed; no_reliable_header
  - Source: "- Creepage Distance - 23 - mm Terminal to Terminal"

### creepage_tb

- Page 3, Table 2, Row 7
  - Value: 23.0 mm
  - Condition: Terminal to Terminal
  - Review: condition_type_mismatch: field=_tb but row has T-T; no_reliable_header; condition_type_mismatch: exp
  - Source: "- Creepage Distance - 23 - mm Terminal to Terminal"

## 11. Figure/Caption Rejection Summary (Step 5.9)

**Total rejected: 7**

| Field ID | Page | Row | source_text |
|----------|------|-----|-------------|
| rds_on_25c | 4 | 1 | Figure 2 Normalized On-Resistance vs. Temperature |
| rds_on_150c | 4 | 1 | Figure 2 Normalized On-Resistance vs. Temperature |
| vgs_th | 4 | 1 | Figure 3 Threshold Voltage vs. Temperature |
| qg | 5 | 2 | Figure 6 Typical Gate Charge Characteristics |
| voltage_rating | 5 | 1 | Figure 7 Typical Capacitances vs. Drain-Source Voltage |
| current_rating | 5 | 1 | Figure 7 Typical Capacitances vs. Drain-Source Voltage |
| current_rating | 5 | 1 | Figure 8 Inductive Switching Energy vs. Drain Current |

## 12. Wrong Dimension Unit Rejection Summary (Step 5.9)

| Metric | Count |
|--------|-------|
| Total wrong dimension rejected | 33 |

| Field ID | Count | Rejected Units |
|----------|-------|----------------|
| ciss | 1 | C |
| coss | 1 | C |
| crss | 2 | C, V |
| current_rating | 4 | C, V, mΩ |
| eoff | 3 | F, Ω |
| eon | 4 | mΩ, Ω |
| err | 2 | V |
| junction_temperature | 6 | A, C, V, Ω |
| qg | 5 | V, g |
| qgs | 1 | V |
| qrr | 1 | Ω |
| rth_jh | 1 | C |
| voltage_rating | 2 | Ω |

**Detail:**

### ciss

- Page 5, Row 0: unit_warning=rejected_wrong_dimension:C
  - source_text: "C ISS"
  - value=None, unit_source=rejected_wrong_dimension:source_text_fallback

### coss

- Page 2, Row 12: unit_warning=rejected_wrong_dimension:C
  - source_text: "C oss Output Capacitance - 0.29 -"
  - value=0.29, unit_source=rejected_wrong_dimension:source_text_fallback

### crss

- Page 5, Row 0: unit_warning=rejected_wrong_dimension:V
  - source_text: "100000 C 10000 ISS )F p ( e1000 c n a tic C a OSS p a C 100 C RSS 10 0 200 400 600 800 1000 1200 Drain-Source Voltage, V..."
  - value=100000.0, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 5, Row 3: unit_warning=rejected_wrong_dimension:C
  - source_text: "C RSS"
  - value=None, unit_source=rejected_wrong_dimension:source_text_fallback

### current_rating

- Page 1, Row 8: unit_warning=rejected_wrong_dimension:mΩ
  - source_text: "R DS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ V =18V; I =150A; T =25C GS D C"
  - value=None, unit_source=rejected_wrong_dimension:unit_column

- Page 2, Row 4: unit_warning=rejected_wrong_dimension:C
  - source_text: "Drain Current (continuous; T =75C) C 240"
  - value=75.0, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 2, Row 6: unit_warning=rejected_wrong_dimension:mΩ
  - source_text: "R DS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ V =18V; I =150A GS D"
  - value=5.3, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 5, Row 0: unit_warning=rejected_wrong_dimension:V
  - source_text: "100000 C 10000 ISS )F p ( e1000 c n a tic C a OSS p a C 100 C RSS 10 0 200 400 600 800 1000 1200 Drain-Source Voltage, V..."
  - value=100000.0, unit_source=rejected_wrong_dimension:source_text_fallback

### eoff

- Page 2, Row 15: unit_warning=rejected_wrong_dimension:F
  - source_text: "E off Turn-off Energy - 7.9 -"
  - value=7.9, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 5, Row 0: unit_warning=rejected_wrong_dimension:Ω
  - source_text: "25 V =-5/+18V GS V =800V DS L=100μH 20 R G(ext) =5Ω E total )Jm 15 ( s so L g E off n ih 10 c tiw S E on 5 0 0 40 80 120..."
  - value=25.0, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 5, Row 2: unit_warning=rejected_wrong_dimension:F
  - source_text: "E off"
  - value=None, unit_source=rejected_wrong_dimension:source_text_fallback

### eon

- Page 1, Row 8: unit_warning=rejected_wrong_dimension:mΩ
  - source_text: "R DS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ V =18V; I =150A; T =25C GS D C"
  - value=None, unit_source=rejected_wrong_dimension:unit_column

- Page 2, Row 6: unit_warning=rejected_wrong_dimension:mΩ
  - source_text: "R DS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ V =18V; I =150A GS D"
  - value=5.3, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 2, Row 14: unit_warning=rejected_wrong_dimension:Ω
  - source_text: "E on Turn-on Energy - 7.1 - mJ V =800V; V =-5/+18V; I =150A; DS GS D R =5Ω; Load=50µH G(ext)"
  - value=7.1, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 5, Row 0: unit_warning=rejected_wrong_dimension:Ω
  - source_text: "25 V =-5/+18V GS V =800V DS L=100μH 20 R G(ext) =5Ω E total )Jm 15 ( s so L g E off n ih 10 c tiw S E on 5 0 0 40 80 120..."
  - value=25.0, unit_source=rejected_wrong_dimension:source_text_fallback

### err

- Page 4, Row 0: unit_warning=rejected_wrong_dimension:V
  - source_text: "600 V GS =20V V GS =18V 500 )A V =16V ( 400 GS SD I ,tn e rru 300 C e c ru V GS =12V o S - 200 n ia rD 100 V =8V GS 0 0 ..."
  - value=600.0, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 5, Row 0: unit_warning=rejected_wrong_dimension:V
  - source_text: "-10 -9 -8 -7 -6 -5 -4 -3 -2 -1 0 0 V =-5V GS -100 V =-2V GS )A ( SD -200 I ,tn V =0V GS e rru C -300 e c ru o S n - -400..."
  - value=None, unit_source=rejected_wrong_dimension:source_text_fallback

### junction_temperature

- Page 1, Row 5: unit_warning=rejected_wrong_dimension:C
  - source_text: "T J; MAX Junction Temperature 175 C"
  - value=175.0, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 1, Row 13: unit_warning=rejected_wrong_dimension:Ω
  - source_text: "Q RR Reverse Recovery Charge - 1839 - nC V =-5/+18V; I =150A; V =800V; GS F R R =5Ω; Load=50µH; T=25C G(ext) J"
  - value=1839.0, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 2, Row 7: unit_warning=rejected_wrong_dimension:C
  - source_text: "T J; MAX Junction Temperature 175 C"
  - value=175.0, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 4, Row 0: unit_warning=rejected_wrong_dimension:A
  - source_text: "2 1.8 1.6 1.4 )no(SD 1.2 R ,e 1 c n a ts ise 0.8 R n O 0.6 0.4 0.2 0 -50 -25 0 25 50 75 100 125 150 175 Junction Tempera..."
  - value=None, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 4, Row 0: unit_warning=rejected_wrong_dimension:V
  - source_text: "3.5 3 2.5 )V ( ht V ,e 2 g a tlo V d 1.5 lo h se rh T 1 0.5 0 -50 -25 0 25 50 75 100 125 150 175 Junction Temperature, T..."
  - value=None, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 4, Row 0: unit_warning=rejected_wrong_dimension:V
  - source_text: "600 V =20V DS 500 )A 400 ( SD I ,tn e T=175℃ rru 300 J C e c ru T J =25℃ o S 200 - n ia T=-55℃ rD J 100 0 0 2 4 6 8 10 1..."
  - value=600.0, unit_source=rejected_wrong_dimension:source_text_fallback

### qg

- Page 1, Row 10: unit_warning=rejected_wrong_dimension:V
  - source_text: "Q G Total Gate Charge - 618 - nC V =800V; V =-5/+18V; I =150A; DD GS D T =25C C"
  - value=618.0, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 2, Row 16: unit_warning=rejected_wrong_dimension:V
  - source_text: "Q GS Gate-Source Charge - 174 - nC V =800V; V =-5/+18V; I =150A DD GS D"
  - value=174.0, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 2, Row 18: unit_warning=rejected_wrong_dimension:g
  - source_text: "Q G Total Gate Charge - 618 -"
  - value=618.0, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 5, Row 0: unit_warning=rejected_wrong_dimension:V
  - source_text: "20 15 )V ( SG V 10 ,e g a tlo V e c 5 ru o S - e ta G 0 -5 0 150 300 450 600 750 Gate Charge, Q (nC) G"
  - value=None, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 5, Row 1: unit_warning=rejected_wrong_dimension:V
  - source_text: "20 15 )V ( SG V 10 ,e g a tlo V e c 5 ru o S - e ta G 0 -5 0 150 300 450 600 750 Gate Charge, Q (nC) G"
  - value=None, unit_source=rejected_wrong_dimension:source_text_fallback

### qgs

- Page 2, Row 16: unit_warning=rejected_wrong_dimension:V
  - source_text: "Q GS Gate-Source Charge - 174 - nC V =800V; V =-5/+18V; I =150A DD GS D"
  - value=174.0, unit_source=rejected_wrong_dimension:source_text_fallback

### qrr

- Page 1, Row 13: unit_warning=rejected_wrong_dimension:Ω
  - source_text: "Q RR Reverse Recovery Charge - 1839 - nC V =-5/+18V; I =150A; V =800V; GS F R R =5Ω; Load=50µH; T=25C G(ext) J"
  - value=1839.0, unit_source=rejected_wrong_dimension:source_text_fallback

### rth_jh

- Page 2, Row 8: unit_warning=rejected_wrong_dimension:C
  - source_text: "R th Jh Thermal Resistance, Junction-to-Heatsink 0.12 C/W"
  - value=0.12, unit_source=rejected_wrong_dimension:source_text_fallback

### voltage_rating

- Page 5, Row 0: unit_warning=rejected_wrong_dimension:Ω
  - source_text: "25 V =-5/+18V GS V =800V DS L=100μH 20 R G(ext) =5Ω E total )Jm 15 ( s so L g E off n ih 10 c tiw S E on 5 0 0 40 80 120..."
  - value=25.0, unit_source=rejected_wrong_dimension:source_text_fallback

- Page 5, Row 0: unit_warning=rejected_wrong_dimension:Ω
  - source_text: "V =-5/+1 GS V =800V DS L=100μH R =5Ω 8V"
  - value=-5.0, unit_source=rejected_wrong_dimension:source_text_fallback
