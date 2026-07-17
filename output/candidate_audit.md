# Candidate Quality Audit

## 1. Candidate Status Breakdown

| Status | Count |
|--------|-------|
| active | 116 |
| rejected | 86 |
| weak | 0 |
| **Total** | **202** |

*active = valid candidates for further processing*
*rejected = rejected by rating guard or policy*
*weak = weak matches reserved for review/LLM*

## 2. 总览

| 指标 | 值 |
|------|---|
| Processed PDFs | ASC300N1200ME3.pdf |
| Total Target Fields | 30 |
| Active Candidates | 116 |
| Matched Fields | 28 |
| Unmatched Fields | 2 |
| Rejected by Rating Guard | 86 |
| Possible Overmatching | 4 |
| Fuzzy Only Match | 0 |

**current_rating**: 67 → 10 (rejected: 57)

**voltage_rating**: 34 → 5 (rejected: 29)

## 3. Field Source Expectation Summary

| Field ID | Label | expected_sources | match_strategy | allow_fuzzy |
|----------|-------|-----------------|----------------|-------------|
| qg | QG (Total Gate Charge) | table | normal | Yes |
| current_rating | Current Rating | title, page_text, table | strict_rating | No |
| junction_temperature | Junction Temperature | table | normal | Yes |
| eon | Eon (Turn-On Energy) | table | normal | Yes |
| voltage_rating | Voltage Rating | title, page_text, table | strict_rating | No |
| rds_on_25c | RDS(on) @25°C | table | normal | Yes |
| rds_on_150c | RDS(on) @150°C | table | normal | Yes |
| qgd | QGD (Gate-Drain Charge) | table | normal | Yes |
| eoff | Eoff (Turn-Off Energy) | table | normal | Yes |
| trr | trr (Reverse Recovery Time) | table | normal | Yes |
| qrr | QRR (Reverse Recovery Charge) | table | normal | Yes |
| module_type | Module Type | table | normal | Yes |
| vgs_th | VGS(th) | table | normal | Yes |
| ciss | Ciss | table | normal | Yes |
| coss | Coss | table | normal | Yes |
| crss | Crss | table | normal | Yes |
| qgs | QGS (Gate-Source Charge) | table | normal | Yes |
| part_number | Part Number | metadata, page_text, table | normal | Yes |
| rth_jh | Rth JH (Junction-to-Heat sink) | table | normal | Yes |
| irrm | IRRM (Reverse Recovery Current) | table | normal | Yes |
| lstray | Lstray (Stray Inductance) | table | normal | Yes |
| weight | Weight | table | normal | Yes |
| isol | Visol (Isolation Voltage) | table | normal | Yes |
| clearance_tt | Clearance T-T (Terminal to Terminal) | table | normal | Yes |
| clearance_tb | Clearance T-B (Terminal to Baseplate) | table | normal | Yes |
| creepage_tt | Creepage T-T (Terminal to Terminal) | table | normal | Yes |
| creepage_tb | Creepage T-B (Terminal to Baseplate) | table | normal | Yes |
| rth_jc | Rth JC (Junction-to-Case) | table | normal | Yes |
| err | Err (Reverse Recovery Energy) | table | normal | Yes |
| manufacturer | Manufacturer | metadata, page_text | metadata_text | No |

## 4. Zero-Candidate Fields

### A. Expected from Text/Metadata (not table)

*These fields are expected to come from metadata or page text, not table extraction.*

| Field ID | Label | expected_sources |
|----------|-------|-----------------|
| manufacturer | Manufacturer | metadata, page_text |

### B. Needs Alias or PDF Check

*These fields have no candidates and may need alias expansion or PDF content check.*

| Field ID | Label | expected_sources |
|----------|-------|-----------------|
| err | Err (Reverse Recovery Energy) | table |

## 5. Candidate Count by Field

| Field ID | Label | Count | Exact | Symbol | Fuzzy | Pages | Warnings |
|----------|-------|-------|-------|--------|-------|-------|----------|
| qg | QG (Total Gate Charge) | 14 | 14 | 0 | 0 | 1, 2, 5 | possible_overmatching |
| current_rating | Current Rating | 10 | 10 | 0 | 0 | 1, 2 | possible_overmatching |
| junction_temperature | Junction Temperature | 10 | 10 | 0 | 0 | 1, 2, 3, 4 | possible_overmatching |
| eon | Eon (Turn-On Energy) | 9 | 5 | 4 | 0 | 1, 2, 5 | possible_overmatching |
| voltage_rating | Voltage Rating | 5 | 5 | 0 | 0 | 1, 2, 5 | - |
| rds_on_25c | RDS(on) @25°C | 5 | 5 | 0 | 0 | 1, 2, 4 | - |
| rds_on_150c | RDS(on) @150°C | 5 | 5 | 0 | 0 | 1, 2, 4 | - |
| qgd | QGD (Gate-Drain Charge) | 5 | 5 | 0 | 0 | 1, 2 | - |
| eoff | Eoff (Turn-Off Energy) | 5 | 5 | 0 | 0 | 2, 5 | - |
| trr | trr (Reverse Recovery Time) | 5 | 2 | 3 | 0 | 2, 3 | - |
| qrr | QRR (Reverse Recovery Charge) | 4 | 4 | 0 | 0 | 1, 3 | - |
| module_type | Module Type | 3 | 3 | 0 | 0 | 1, 7 | - |
| vgs_th | VGS(th) | 3 | 3 | 0 | 0 | 2, 4 | - |
| ciss | Ciss | 3 | 3 | 0 | 0 | 2, 5 | - |
| coss | Coss | 3 | 3 | 0 | 0 | 2, 5 | - |
| crss | Crss | 3 | 3 | 0 | 0 | 2, 5 | - |
| qgs | QGS (Gate-Source Charge) | 3 | 3 | 0 | 0 | 2 | - |
| part_number | Part Number | 2 | 2 | 0 | 0 | 1, 7 | - |
| rth_jh | Rth JH (Junction-to-Heat sink) | 2 | 2 | 0 | 0 | 2 | - |
| irrm | IRRM (Reverse Recovery Current) | 2 | 2 | 0 | 0 | 3 | - |
| lstray | Lstray (Stray Inductance) | 2 | 2 | 0 | 0 | 3 | - |
| weight | Weight | 2 | 2 | 0 | 0 | 3 | - |
| isol | Visol (Isolation Voltage) | 2 | 2 | 0 | 0 | 3 | - |
| clearance_tt | Clearance T-T (Terminal to Terminal) | 2 | 2 | 0 | 0 | 3 | - |
| clearance_tb | Clearance T-B (Terminal to Baseplate) | 2 | 2 | 0 | 0 | 3 | - |
| creepage_tt | Creepage T-T (Terminal to Terminal) | 2 | 2 | 0 | 0 | 3 | - |
| creepage_tb | Creepage T-B (Terminal to Baseplate) | 2 | 2 | 0 | 0 | 3 | - |
| rth_jc | Rth JC (Junction-to-Case) | 1 | 0 | 1 | 0 | 8 | - |
| err | Err (Reverse Recovery Energy) | 0 | 0 | 0 | 0 |  | - |
| manufacturer | Manufacturer | 0 | 0 | 0 | 0 |  | - |

## 6. Accepted Rating Candidates

*current_rating and voltage_rating candidates that passed the rating guard*

### current_rating (Current Rating)

Total: 10 accepted candidates

**Page 1, Table 1, Row 3**
- matched_alias: `current`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_current
- source_text: "ID Drain Current (continuous) 300 A TC=25C"

**Page 1, Table 2, Row 5**
- matched_alias: `current`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_current
- source_text: "ID Drain Current (continuous) A"

**Page 2, Table 0, Row 3**
- matched_alias: `current`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_current
- source_text: "ID Drain Current (continuous; TC=25C) 300 A"

**Page 2, Table 0, Row 4**
- matched_alias: `current`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_current
- source_text: "Drain Current (continuous; TC=75C) 240"

**Page 2, Table 0, Row 5**
- matched_alias: `current`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_current
- source_text: "IDM Drain Current (pulsed) 480 A"

**Page 2, Table 1, Row 3**
- matched_alias: `current`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_current
- source_text: "IDSS Zero Gate Voltage Drain Current - - 150 μA VDS=1200V; VGS=0V"

**Page 2, Table 2, Row 4**
- matched_alias: `current`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_current
- source_text: "Drain Current (continuous; TC=25C) 300"

**Page 2, Table 2, Row 6**
- matched_alias: `current`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_current
- source_text: "Drain Current (continuous; TC=75C) 240"

**Page 2, Table 2, Row 7**
- matched_alias: `current`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_current
- source_text: "IDM Drain Current (pulsed) 480 A"

**Page 2, Table 4, Row 3**
- matched_alias: `current`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_current
- source_text: "IDSS Zero Gate Voltage Drain Current - - 150 μA VDS=1200V; VGS=0V"

### voltage_rating (Voltage Rating)

Total: 5 accepted candidates

**Page 1, Table 1, Row 2**
- matched_alias: `voltage`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_source_voltage
- source_text: "VDS Drain-Source Voltage 1200 V TC=25C"

**Page 1, Table 2, Row 3**
- matched_alias: `voltage`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_source_voltage
- source_text: "VDS Drain-Source Voltage 1200 V TC=25C"

**Page 2, Table 0, Row 1**
- matched_alias: `voltage`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_source_voltage
- source_text: "VDS Drain-Source Voltage 1200 V"

**Page 2, Table 2, Row 2**
- matched_alias: `voltage`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_source_voltage
- source_text: "VDS Drain-Source Voltage 1200 V"

**Page 5, Table 1, Row 16**
- matched_alias: `voltage`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_source_voltage
- source_text: "Drain-Source Voltage, VDS (V) Gate Charge, QG (nC)"

## 7. Rejected Rating Candidates

*current_rating and voltage_rating candidates rejected by rating guard*

### current_rating (Current Rating) - 57 rejected

**Rejected by**: `IC_too_broad_without_current_context` (matched_alias: `IC`, count: 29)
  - Page 1, Table 1, Row 7: "Static characteristics"
  - Page 1, Table 1, Row 9: "Dynamic characteristics"
  - Page 1, Table 2, Row 9: "Static characteristics"

**Rejected by**: `ID_too_broad_without_context` (matched_alias: `ID`, count: 19)
  - Page 1, Table 1, Row 8: "RDS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ VGS=18V; ID=150A; TC=25C"
  - Page 1, Table 1, Row 10: "QG Total Gate Charge - 618 - nC VDD=800V; VGS=-5/+18V; ID=150A; TC=25C"
  - Page 1, Table 2, Row 10: "RDS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ VGS=18V; ID=150A; TC=25C"

**Rejected by**: `leakage_current_not_rating` (matched_alias: `current`, count: 2)
  - Page 2, Table 1, Row 4: "IGSS Gate-Body Leakage Current - - 1.5 μA VGS=-10/20V; VDS=0V"
  - Page 2, Table 4, Row 4: "IGSS Gate-Body Leakage Current - - 1.5 μA VGS=-10/20V; VDS=0V"

**Rejected by**: `forward_current_not_rating` (matched_alias: `current`, count: 2)
  - Page 3, Table 0, Row 2: "IS Continuous Diode Forward Current - 150 - A VGS=0V; TC=25C"
  - Page 3, Table 2, Row 3: "IS Continuous Diode Forward Current - 150 - A VGS=0V; TC=25C"

**Rejected by**: `reverse_recovery_current_not_rating` (matched_alias: `current`, count: 2)
  - Page 3, Table 0, Row 5: "IRRM Peak Reverse Recovery Current - 141 - A"
  - Page 3, Table 2, Row 8: "IRRM Peak Reverse Recovery Current - 141 - A"

**Rejected by**: `too_broad_without_context` (matched_alias: `current`, count: 3)
  - Page 4, Table 0, Row 9: "Drain-Source Current, IDS(A) 300 On Resistance, RDS(on) 1"
  - Page 4, Table 1, Row 9: "1.5 Drain-Source Current, IDS(A)"
  - Page 5, Table 0, Row 5: "80 Drain-Source Current, IDS (A) 120 160 200"


### voltage_rating (Voltage Rating) - 29 rejected

**Rejected by**: `gate_voltage_not_rating` (matched_alias: `voltage`, count: 5)
  - Page 2, Table 0, Row 2: "VGS Gate-Source Voltage (dynamic) -10/+22 V"
  - Page 2, Table 1, Row 3: "IDSS Zero Gate Voltage Drain Current - - 150 μA VDS=1200V; VGS=0V"
  - Page 2, Table 2, Row 3: "VGS Gate-Source Voltage (dynamic) -10/+22 V"

**Rejected by**: `test_condition_vgs_not_rating` (matched_alias: `voltage`, count: 4)
  - Page 2, Table 1, Row 2: "BVDS Drain-Source Breakdown Voltage 1200 - - V VGS=0V"
  - Page 2, Table 4, Row 2: "BVDS Drain-Source Breakdown Voltage 1200 - - V VGS=0V"
  - Page 3, Table 0, Row 1: "VFSD Forward Voltage - 3.5 6 V VGS=0V; IF=150A"

**Rejected by**: `test_condition_vds_not_rating` (matched_alias: `VDS`, count: 11)
  - Page 2, Table 1, Row 4: "IGSS Gate-Body Leakage Current - - 1.5 μA VGS=-10/20V; VDS=0V"
  - Page 2, Table 1, Row 11: "Ciss Input Capacitance - 9.15 - nF VDS=1000V; f=1MHz; VAC=25mV"
  - Page 2, Table 1, Row 14: "Eon Turn-on Energy - 7.1 - mJ VDS=800V; VGS=-5/+18V; ID=150A; RG(ext)=5Ω; Load=50µH"

**Rejected by**: `test_condition_vds_not_rating` (matched_alias: `voltage`, count: 2)
  - Page 2, Table 1, Row 5: "VGS(th) Gate Threshold Voltage 2 - 4 V VDS=VGS; ID=30mA"
  - Page 2, Table 4, Row 5: "VGS(th) Gate Threshold Voltage 2 - 4 V VDS=VGS; ID=30mA"

**Rejected by**: `too_broad_without_context` (matched_alias: `voltage`, count: 4)
  - Page 2, Table 1, Row 7: "VGS(on) Recommended Turn-on Voltage - 18 - V Static"
  - Page 2, Table 1, Row 8: "VGS(off) Recommended Turn-off Voltage - -5 -"
  - Page 2, Table 4, Row 7: "VGS(on) Recommended Turn-on Voltage - 18 -"

**Rejected by**: `isolation_voltage_not_rating` (matched_alias: `voltage`, count: 2)
  - Page 3, Table 1, Row 4: "Visol Case Isolation Voltage (DC; t=1min) 4.2 - - kV"
  - Page 3, Table 3, Row 5: "Visol Case Isolation Voltage (DC; t=1min) 4.2 - - kV"

**Rejected by**: `threshold_voltage_not_rating` (matched_alias: `voltage`, count: 1)
  - Page 4, Table 1, Row 8: "Threshold Voltage, Vth(V) 300"


## 8. Candidate Examples by Field

*Each field shows up to 3 example candidates*

### qg (QG (Total Gate Charge))

Total: 14 candidates | Exact: 14 | Symbol: 0 | Fuzzy: 0
Warnings: possible_overmatching

**Page 1, Table 1, Row 10**
- matched_alias: `QG`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "QG Total Gate Charge - 618 - nC VDD=800V; VGS=-5/+18V; ID=150A; TC=25C"

**Page 1, Table 1, Row 11**
- matched_alias: `QG`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "QGD Gate-Drain Charge - 147 -"

**Page 1, Table 2, Row 12**
- matched_alias: `QG`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "QG Total Gate Charge - 618 -"


### current_rating (Current Rating)

Total: 10 candidates | Exact: 10 | Symbol: 0 | Fuzzy: 0
Warnings: possible_overmatching

**Page 1, Table 1, Row 3**
- matched_alias: `current`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_current
- confidence: 0.95
- source_text: "ID Drain Current (continuous) 300 A TC=25C"

**Page 1, Table 2, Row 5**
- matched_alias: `current`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_current
- confidence: 0.95
- source_text: "ID Drain Current (continuous) A"

**Page 2, Table 0, Row 3**
- matched_alias: `current`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_current
- confidence: 0.95
- source_text: "ID Drain Current (continuous; TC=25C) 300 A"


### junction_temperature (Junction Temperature)

Total: 10 candidates | Exact: 10 | Symbol: 0 | Fuzzy: 0
Warnings: possible_overmatching

**Page 1, Table 1, Row 5**
- matched_alias: `TJ`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "TJ; MAX Junction Temperature 175 C"

**Page 1, Table 1, Row 13**
- matched_alias: `TJ`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "QRR Reverse Recovery Charge - 1839 - nC VGS=-5/+18V; IF=150A; VR=800V; RG(ext)=5Ω; Load=50µH; TJ=25C"

**Page 1, Table 2, Row 7**
- matched_alias: `TJ`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "TJ; MAX Junction Temperature 175 C"


### eon (Eon (Turn-On Energy))

Total: 9 candidates | Exact: 5 | Symbol: 4 | Fuzzy: 0
Warnings: possible_overmatching

**Page 1, Table 1, Row 8**
- matched_alias: `Eon`
- match_type: symbol
- match_policy: normal
- confidence: 0.85
- source_text: "RDS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ VGS=18V; ID=150A; TC=25C"

**Page 1, Table 2, Row 10**
- matched_alias: `Eon`
- match_type: symbol
- match_policy: normal
- confidence: 0.85
- source_text: "RDS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ VGS=18V; ID=150A; TC=25C"

**Page 2, Table 1, Row 6**
- matched_alias: `Eon`
- match_type: symbol
- match_policy: normal
- confidence: 0.85
- source_text: "RDS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ VGS=18V; ID=150A"


### voltage_rating (Voltage Rating)

Total: 5 candidates | Exact: 5 | Symbol: 0 | Fuzzy: 0

**Page 1, Table 1, Row 2**
- matched_alias: `voltage`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_source_voltage
- confidence: 0.95
- source_text: "VDS Drain-Source Voltage 1200 V TC=25C"

**Page 1, Table 2, Row 3**
- matched_alias: `voltage`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_source_voltage
- confidence: 0.95
- source_text: "VDS Drain-Source Voltage 1200 V TC=25C"

**Page 2, Table 0, Row 1**
- matched_alias: `voltage`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_source_voltage
- confidence: 0.95
- source_text: "VDS Drain-Source Voltage 1200 V"


### rds_on_25c (RDS(on) @25°C)

Total: 5 candidates | Exact: 5 | Symbol: 0 | Fuzzy: 0

**Page 1, Table 1, Row 8**
- matched_alias: `RDS(on)`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "RDS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ VGS=18V; ID=150A; TC=25C"

**Page 1, Table 2, Row 10**
- matched_alias: `RDS(on)`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "RDS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ VGS=18V; ID=150A; TC=25C"

**Page 2, Table 1, Row 6**
- matched_alias: `RDS(on)`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "RDS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ VGS=18V; ID=150A"


### rds_on_150c (RDS(on) @150°C)

Total: 5 candidates | Exact: 5 | Symbol: 0 | Fuzzy: 0

**Page 1, Table 1, Row 8**
- matched_alias: `RDS(on)`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "RDS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ VGS=18V; ID=150A; TC=25C"

**Page 1, Table 2, Row 10**
- matched_alias: `RDS(on)`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "RDS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ VGS=18V; ID=150A; TC=25C"

**Page 2, Table 1, Row 6**
- matched_alias: `RDS(on)`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "RDS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ VGS=18V; ID=150A"


### qgd (QGD (Gate-Drain Charge))

Total: 5 candidates | Exact: 5 | Symbol: 0 | Fuzzy: 0

**Page 1, Table 1, Row 11**
- matched_alias: `Qgd`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "QGD Gate-Drain Charge - 147 -"

**Page 1, Table 2, Row 16**
- matched_alias: `Qgd`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "QGD Gate-Drain Charge - 147 -"

**Page 2, Table 1, Row 17**
- matched_alias: `Qgd`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "QGD Gate-Drain Charge - 147 -"


### eoff (Eoff (Turn-Off Energy))

Total: 5 candidates | Exact: 5 | Symbol: 0 | Fuzzy: 0

**Page 2, Table 1, Row 15**
- matched_alias: `Eoff`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "Eoff Turn-off Energy - 7.9 -"

**Page 2, Table 3, Row 2**
- matched_alias: `Eoff`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "Eoff Turn-off Energy - 7.9 -"

**Page 2, Table 4, Row 20**
- matched_alias: `Eoff`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "Eoff Turn-off Energy - 7.9 -"


### trr (trr (Reverse Recovery Time))

Total: 5 candidates | Exact: 2 | Symbol: 3 | Fuzzy: 0

**Page 2, Table 1, Row 20**
- matched_alias: `trr`
- match_type: symbol
- match_policy: normal
- confidence: 0.85
- source_text: "tr Rise Time - 42 -"

**Page 2, Table 3, Row 7**
- matched_alias: `trr`
- match_type: symbol
- match_policy: normal
- confidence: 0.85
- source_text: "tr Rise Time - 42 -"

**Page 2, Table 4, Row 25**
- matched_alias: `trr`
- match_type: symbol
- match_policy: normal
- confidence: 0.85
- source_text: "tr Rise Time - 42 -"


### qrr (QRR (Reverse Recovery Charge))

Total: 4 candidates | Exact: 4 | Symbol: 0 | Fuzzy: 0

**Page 1, Table 1, Row 13**
- matched_alias: `Qrr`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "QRR Reverse Recovery Charge - 1839 - nC VGS=-5/+18V; IF=150A; VR=800V; RG(ext)=5Ω; Load=50µH; TJ=25C"

**Page 1, Table 2, Row 19**
- matched_alias: `Qrr`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "QRR Reverse Recovery Charge - 1839 - nC"

**Page 3, Table 0, Row 4**
- matched_alias: `Qrr`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "QRR Reverse Recovery Charge - 1839 - nC"


### module_type (Module Type)

Total: 3 candidates | Exact: 3 | Symbol: 0 | Fuzzy: 0

**Page 1, Table 0, Row 2**
- matched_alias: `package`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "Package Type ME3"

**Page 7, Table 1, Row 3**
- matched_alias: `package`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "Package Dimensions (mm)"

**Page 7, Table 1, Row 4**
- matched_alias: `package`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "Package Type：ME3"


### vgs_th (VGS(th))

Total: 3 candidates | Exact: 3 | Symbol: 0 | Fuzzy: 0

**Page 2, Table 1, Row 5**
- matched_alias: `VGS(th)`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "VGS(th) Gate Threshold Voltage 2 - 4 V VDS=VGS; ID=30mA"

**Page 2, Table 4, Row 5**
- matched_alias: `VGS(th)`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "VGS(th) Gate Threshold Voltage 2 - 4 V VDS=VGS; ID=30mA"

**Page 4, Table 1, Row 8**
- matched_alias: `Vth`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "Threshold Voltage, Vth(V) 300"


### ciss (Ciss)

Total: 3 candidates | Exact: 3 | Symbol: 0 | Fuzzy: 0

**Page 2, Table 1, Row 11**
- matched_alias: `Ciss`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "Ciss Input Capacitance - 9.15 - nF VDS=1000V; f=1MHz; VAC=25mV"

**Page 2, Table 4, Row 12**
- matched_alias: `Ciss`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "Ciss Input Capacitance - 9.15 -"

**Page 5, Table 2, Row 5**
- matched_alias: `Ciss`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "CISS"


### coss (Coss)

Total: 3 candidates | Exact: 3 | Symbol: 0 | Fuzzy: 0

**Page 2, Table 1, Row 12**
- matched_alias: `Coss`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "Coss Output Capacitance - 0.29 -"

**Page 2, Table 4, Row 14**
- matched_alias: `Coss`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "Coss Output Capacitance - 0.29 - VDS=1000V; f=1MHz; VAC=25mV"

**Page 5, Table 2, Row 11**
- matched_alias: `Coss`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "COSS 10"


### crss (Crss)

Total: 3 candidates | Exact: 3 | Symbol: 0 | Fuzzy: 0

**Page 2, Table 1, Row 13**
- matched_alias: `Crss`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "Crss Reverse Transfer Capacitance - 45 - pF"

**Page 2, Table 4, Row 15**
- matched_alias: `Crss`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "Crss Reverse Transfer Capacitance - 45 - pF"

**Page 5, Table 2, Row 14**
- matched_alias: `Crss`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "CRSS 5"


### qgs (QGS (Gate-Source Charge))

Total: 3 candidates | Exact: 3 | Symbol: 0 | Fuzzy: 0

**Page 2, Table 1, Row 16**
- matched_alias: `Qgs`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "QGS Gate-Source Charge - 174 - nC VDD=800V; VGS=-5/+18V; ID=150A"

**Page 2, Table 3, Row 3**
- matched_alias: `Qgs`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "QGS Gate-Source Charge - 174 -"

**Page 2, Table 4, Row 21**
- matched_alias: `Qgs`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "QGS Gate-Source Charge - 174 -"


### part_number (Part Number)

Total: 2 candidates | Exact: 2 | Symbol: 0 | Fuzzy: 0

**Page 1, Table 0, Row 2**
- matched_alias: `type`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "Package Type ME3"

**Page 7, Table 1, Row 4**
- matched_alias: `type`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "Package Type：ME3"


### rth_jh (Rth JH (Junction-to-Heat sink))

Total: 2 candidates | Exact: 2 | Symbol: 0 | Fuzzy: 0

**Page 2, Table 0, Row 8**
- matched_alias: `Rth JH`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "Rth Jh Thermal Resistance, Junction-to-Heatsink 0.12 C/W"

**Page 2, Table 2, Row 10**
- matched_alias: `Rth JH`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "Rth Jh Thermal Resistance, Junction-to-Heatsink 0.12 C/W"


### irrm (IRRM (Reverse Recovery Current))

Total: 2 candidates | Exact: 2 | Symbol: 0 | Fuzzy: 0

**Page 3, Table 0, Row 5**
- matched_alias: `IRRM`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "IRRM Peak Reverse Recovery Current - 141 - A"

**Page 3, Table 2, Row 8**
- matched_alias: `IRRM`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "IRRM Peak Reverse Recovery Current - 141 - A"


### lstray (Lstray (Stray Inductance))

Total: 2 candidates | Exact: 2 | Symbol: 0 | Fuzzy: 0

**Page 3, Table 1, Row 1**
- matched_alias: `Lstray`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "LStray Stray Inductance - 20 - nH"

**Page 3, Table 3, Row 2**
- matched_alias: `Lstray`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "LStray Stray Inductance - 20 - nH"


### weight (Weight)

Total: 2 candidates | Exact: 2 | Symbol: 0 | Fuzzy: 0

**Page 3, Table 1, Row 2**
- matched_alias: `weight`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "W Weight - 340 - g"

**Page 3, Table 3, Row 3**
- matched_alias: `weight`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "W Weight - 340 - g"


### isol (Visol (Isolation Voltage))

Total: 2 candidates | Exact: 2 | Symbol: 0 | Fuzzy: 0

**Page 3, Table 1, Row 4**
- matched_alias: `Visol`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "Visol Case Isolation Voltage (DC; t=1min) 4.2 - - kV"

**Page 3, Table 3, Row 5**
- matched_alias: `Visol`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "Visol Case Isolation Voltage (DC; t=1min) 4.2 - - kV"


### clearance_tt (Clearance T-T (Terminal to Terminal))

Total: 2 candidates | Exact: 2 | Symbol: 0 | Fuzzy: 0

**Page 3, Table 1, Row 5**
- matched_alias: `clearance`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "- Clearance Distance - 11 - mm Terminal to Terminal"

**Page 3, Table 3, Row 7**
- matched_alias: `clearance`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "- Clearance Distance"


### clearance_tb (Clearance T-B (Terminal to Baseplate))

Total: 2 candidates | Exact: 2 | Symbol: 0 | Fuzzy: 0

**Page 3, Table 1, Row 5**
- matched_alias: `clearance`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "- Clearance Distance - 11 - mm Terminal to Terminal"

**Page 3, Table 3, Row 7**
- matched_alias: `clearance`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "- Clearance Distance"


### creepage_tt (Creepage T-T (Terminal to Terminal))

Total: 2 candidates | Exact: 2 | Symbol: 0 | Fuzzy: 0

**Page 3, Table 1, Row 7**
- matched_alias: `creepage`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "- Creepage Distance - 23 - mm Terminal to Terminal"

**Page 3, Table 3, Row 10**
- matched_alias: `creepage`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "- Creepage Distance"


### creepage_tb (Creepage T-B (Terminal to Baseplate))

Total: 2 candidates | Exact: 2 | Symbol: 0 | Fuzzy: 0

**Page 3, Table 1, Row 7**
- matched_alias: `creepage`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "- Creepage Distance - 23 - mm Terminal to Terminal"

**Page 3, Table 3, Row 10**
- matched_alias: `creepage`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "- Creepage Distance"


### rth_jc (Rth JC (Junction-to-Case))

Total: 1 candidates | Exact: 0 | Symbol: 1 | Fuzzy: 0

**Page 8, Table 0, Row 13**
- matched_alias: `Rth`
- match_type: symbol
- match_policy: normal
- confidence: 0.85
- source_text: "customer’s technical departments to evaluate the suitability of the product for the intended application and the"


