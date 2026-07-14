# Candidate Quality Audit

## 1. Candidate Status Breakdown

| Status | Count |
|--------|-------|
| active | 77 |
| rejected | 30 |
| weak | 0 |
| **Total** | **107** |

*active = valid candidates for further processing*
*rejected = rejected by rating guard or policy*
*weak = weak matches reserved for review/LLM*

## 2. 总览

| 指标 | 值 |
|------|---|
| Processed PDFs | ASC300N1200ME3.pdf |
| Total Target Fields | 30 |
| Active Candidates | 77 |
| Matched Fields | 28 |
| Unmatched Fields | 2 |
| Rejected by Rating Guard | 30 |
| Possible Overmatching | 2 |
| Fuzzy Only Match | 0 |

**current_rating**: 31 → 10 (rejected: 21)

**voltage_rating**: 20 → 11 (rejected: 9)

## 3. Field Source Expectation Summary

| Field ID | Label | expected_sources | match_strategy | allow_fuzzy |
|----------|-------|-----------------|----------------|-------------|
| voltage_rating | Voltage Rating | title, page_text, table | strict_rating | No |
| current_rating | Current Rating | title, page_text, table | strict_rating | No |
| qg | QG (Total Gate Charge) | table | normal | Yes |
| junction_temperature | Junction Temperature | table | normal | Yes |
| eon | Eon (Turn-On Energy) | table | normal | Yes |
| rds_on_25c | RDS(on) @25°C | table | normal | Yes |
| rds_on_150c | RDS(on) @150°C | table | normal | Yes |
| crss | Crss | table | normal | Yes |
| eoff | Eoff (Turn-Off Energy) | table | normal | Yes |
| qgd | QGD (Gate-Drain Charge) | table | normal | Yes |
| qrr | QRR (Reverse Recovery Charge) | table | normal | Yes |
| vgs_th | VGS(th) | table | normal | Yes |
| ciss | Ciss | table | normal | Yes |
| trr | trr (Reverse Recovery Time) | table | normal | Yes |
| err | Err (Reverse Recovery Energy) | table | normal | Yes |
| part_number | Part Number | metadata, page_text, table | normal | Yes |
| module_type | Module Type | table | normal | Yes |
| rth_jh | Rth JH (Junction-to-Heat sink) | table | normal | Yes |
| coss | Coss | table | normal | Yes |
| qgs | QGS (Gate-Source Charge) | table | normal | Yes |
| irrm | IRRM (Reverse Recovery Current) | table | normal | Yes |
| lstray | Lstray (Stray Inductance) | table | normal | Yes |
| weight | Weight | table | normal | Yes |
| isol | Visol (Isolation Voltage) | table | normal | Yes |
| clearance_tt | Clearance T-T (Terminal to Terminal) | table | normal | Yes |
| clearance_tb | Clearance T-B (Terminal to Baseplate) | table | normal | Yes |
| creepage_tt | Creepage T-T (Terminal to Terminal) | table | normal | Yes |
| creepage_tb | Creepage T-B (Terminal to Baseplate) | table | normal | Yes |
| manufacturer | Manufacturer | metadata, page_text | metadata_text | No |
| rth_jc | Rth JC (Junction-to-Case) | table | normal | Yes |

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
| rth_jc | Rth JC (Junction-to-Case) | table |

## 5. Candidate Count by Field

| Field ID | Label | Count | Exact | Symbol | Fuzzy | Pages | Warnings |
|----------|-------|-------|-------|--------|-------|-------|----------|
| voltage_rating | Voltage Rating | 11 | 7 | 4 | 0 | 1, 2, 4, 5 | possible_overmatching |
| current_rating | Current Rating | 10 | 10 | 0 | 0 | 1, 2, 5 | possible_overmatching |
| qg | QG (Total Gate Charge) | 8 | 5 | 3 | 0 | 1, 2, 5 | - |
| junction_temperature | Junction Temperature | 6 | 4 | 2 | 0 | 1, 2, 4 | - |
| eon | Eon (Turn-On Energy) | 5 | 1 | 4 | 0 | 1, 2, 5 | - |
| rds_on_25c | RDS(on) @25°C | 3 | 1 | 2 | 0 | 1, 2, 4 | - |
| rds_on_150c | RDS(on) @150°C | 3 | 1 | 2 | 0 | 1, 2, 4 | - |
| crss | Crss | 3 | 1 | 2 | 0 | 2, 5 | - |
| eoff | Eoff (Turn-Off Energy) | 3 | 1 | 2 | 0 | 2, 5 | - |
| qgd | QGD (Gate-Drain Charge) | 2 | 2 | 0 | 0 | 1, 2 | - |
| qrr | QRR (Reverse Recovery Charge) | 2 | 2 | 0 | 0 | 1, 3 | - |
| vgs_th | VGS(th) | 2 | 2 | 0 | 0 | 2, 4 | - |
| ciss | Ciss | 2 | 1 | 1 | 0 | 2, 5 | - |
| trr | trr (Reverse Recovery Time) | 2 | 1 | 1 | 0 | 2, 3 | - |
| err | Err (Reverse Recovery Energy) | 2 | 0 | 2 | 0 | 4, 5 | - |
| part_number | Part Number | 1 | 1 | 0 | 0 | 1 | - |
| module_type | Module Type | 1 | 1 | 0 | 0 | 1 | - |
| rth_jh | Rth JH (Junction-to-Heat sink) | 1 | 0 | 1 | 0 | 2 | - |
| coss | Coss | 1 | 1 | 0 | 0 | 2 | - |
| qgs | QGS (Gate-Source Charge) | 1 | 1 | 0 | 0 | 2 | - |
| irrm | IRRM (Reverse Recovery Current) | 1 | 1 | 0 | 0 | 3 | - |
| lstray | Lstray (Stray Inductance) | 1 | 1 | 0 | 0 | 3 | - |
| weight | Weight | 1 | 1 | 0 | 0 | 3 | - |
| isol | Visol (Isolation Voltage) | 1 | 1 | 0 | 0 | 3 | - |
| clearance_tt | Clearance T-T (Terminal to Terminal) | 1 | 1 | 0 | 0 | 3 | - |
| clearance_tb | Clearance T-B (Terminal to Baseplate) | 1 | 1 | 0 | 0 | 3 | - |
| creepage_tt | Creepage T-T (Terminal to Terminal) | 1 | 1 | 0 | 0 | 3 | - |
| creepage_tb | Creepage T-B (Terminal to Baseplate) | 1 | 1 | 0 | 0 | 3 | - |
| manufacturer | Manufacturer | 0 | 0 | 0 | 0 |  | - |
| rth_jc | Rth JC (Junction-to-Case) | 0 | 0 | 0 | 0 |  | - |

## 6. Accepted Rating Candidates

*current_rating and voltage_rating candidates that passed the rating guard*

### current_rating (Current Rating)

Total: 10 accepted candidates

**Page 1, Table 2, Row 3**
- matched_alias: `current`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_current
- source_text: "I D Drain Current (continuous) 300 A T =25C C"

**Page 1, Table 2, Row 8**
- matched_alias: `IC`
- match_type: exact
- match_policy: strict_rating
- accept_reason: strong_current_context
- source_text: "R DS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ V =18V; I =150A; T =25C GS D C"

**Page 2, Table 1, Row 3**
- matched_alias: `current`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_current
- source_text: "I D Drain Current (continuous; T =25C) C 300 A"

**Page 2, Table 1, Row 4**
- matched_alias: `current`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_current
- source_text: "Drain Current (continuous; T =75C) C 240"

**Page 2, Table 1, Row 5**
- matched_alias: `current`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_current
- source_text: "I DM Drain Current (pulsed) 480 A"

**Page 2, Table 2, Row 3**
- matched_alias: `current`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_current
- source_text: "I DSS Zero Gate Voltage Drain Current - - 150 μA V =1200V; V =0V DS GS"

**Page 2, Table 2, Row 6**
- matched_alias: `IC`
- match_type: exact
- match_policy: strict_rating
- accept_reason: strong_current_context
- source_text: "R DS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ V =18V; I =150A GS D"

**Page 5, Table 5, Row 0**
- matched_alias: `IC`
- match_type: exact
- match_policy: strict_rating
- accept_reason: strong_current_context
- source_text: "100000 C 10000 ISS )F p ( e1000 c n a tic C a OSS p a C 100 C RSS 10 0 200 400 600 800 1000 1200 Drain-Source Voltage, V (V) DS"

**Page 5, Table 5, Row 1**
- matched_alias: `IC`
- match_type: exact
- match_policy: strict_rating
- accept_reason: strong_current_context
- source_text: "Figure 7 Typical Capacitances vs. Drain-Source Voltage"

**Page 5, Table 6, Row 1**
- matched_alias: `current`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_current
- source_text: "Figure 8 Inductive Switching Energy vs. Drain Current"

### voltage_rating (Voltage Rating)

Total: 11 accepted candidates

**Page 1, Table 2, Row 2**
- matched_alias: `voltage`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_source_voltage
- source_text: "V DS Drain-Source Voltage 1200 V T =25C C"

**Page 2, Table 1, Row 1**
- matched_alias: `voltage`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_source_voltage
- source_text: "V DS Drain-Source Voltage 1200 V"

**Page 2, Table 2, Row 2**
- matched_alias: `voltage`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_breakdown_voltage
- source_text: "BV DS Drain-Source Breakdown Voltage 1200 - - V V =0V GS"

**Page 2, Table 2, Row 11**
- matched_alias: `VDS`
- match_type: symbol
- match_policy: strict_rating
- accept_reason: strong_rating_context
- source_text: "C iss Input Capacitance - 9.15 - nF V =1000V; f=1MHz; V =25mV DS AC"

**Page 4, Table 1, Row 0**
- matched_alias: `voltage`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_source_voltage
- source_text: "600 V GS =20V V GS =18V 500 )A V =16V ( 400 GS SD I ,tn e rru 300 C e c ru V GS =12V o S - 200 n ia rD 100 V =8V GS 0 0 2 4 6 8 Drain-Source Voltage, V (V) DS"

**Page 4, Table 8, Row 0**
- matched_alias: `VDS`
- match_type: symbol
- match_policy: strict_rating
- accept_reason: strong_rating_context
- source_text: "V =20V DS"

**Page 5, Table 1, Row 0**
- matched_alias: `voltage`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_source_voltage
- source_text: "-10 -9 -8 -7 -6 -5 -4 -3 -2 -1 0 0 V =-5V GS -100 V =-2V GS )A ( SD -200 I ,tn V =0V GS e rru C -300 e c ru o S n - -400 ia rD -500 -600 Drain-Source Voltage, V (V) DS"

**Page 5, Table 5, Row 0**
- matched_alias: `voltage`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_source_voltage
- source_text: "100000 C 10000 ISS )F p ( e1000 c n a tic C a OSS p a C 100 C RSS 10 0 200 400 600 800 1000 1200 Drain-Source Voltage, V (V) DS"

**Page 5, Table 5, Row 1**
- matched_alias: `voltage`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_source_voltage
- source_text: "Figure 7 Typical Capacitances vs. Drain-Source Voltage"

**Page 5, Table 6, Row 0**
- matched_alias: `VDS`
- match_type: symbol
- match_policy: strict_rating
- accept_reason: strong_rating_context
- source_text: "25 V =-5/+18V GS V =800V DS L=100μH 20 R G(ext) =5Ω E total )Jm 15 ( s so L g E off n ih 10 c tiw S E on 5 0 0 40 80 120 160 200 Drain-Source Current, I (A) DS"

**Page 5, Table 8, Row 0**
- matched_alias: `VDS`
- match_type: symbol
- match_policy: strict_rating
- accept_reason: strong_rating_context
- source_text: "V =-5/+1 GS V =800V DS L=100μH R =5Ω 8V"

## 7. Rejected Rating Candidates

*current_rating and voltage_rating candidates rejected by rating guard*

### current_rating (Current Rating) - 21 rejected

**Rejected by**: `IC_too_broad_without_current_context` (matched_alias: `IC`, count: 10)
  - Page 1, Table 2, Row 7: "Static characteristics"
  - Page 1, Table 2, Row 9: "Dynamic characteristics"
  - Page 2, Table 1, Row 2: "V GS Gate-Source Voltage (dynamic) -10/+22 V"

**Rejected by**: `ID_too_broad_without_context` (matched_alias: `ID`, count: 7)
  - Page 2, Table 0, Row 1: "1200V, Half-Bridge, Silicon Carbide MOSFET Module"
  - Page 3, Table 0, Row 1: "1200V, Half-Bridge, Silicon Carbide MOSFET Module"
  - Page 4, Table 0, Row 1: "1200V, Half-Bridge, Silicon Carbide MOSFET Module"

**Rejected by**: `leakage_current_not_rating` (matched_alias: `current`, count: 1)
  - Page 2, Table 2, Row 4: "I GSS Gate-Body Leakage Current - - 1.5 μA V =-10/20V; V =0V GS DS"

**Rejected by**: `forward_current_not_rating` (matched_alias: `current`, count: 1)
  - Page 3, Table 1, Row 2: "I S Continuous Diode Forward Current - 150 - A V =0V; T =25C GS C"

**Rejected by**: `too_broad_without_context` (matched_alias: `current`, count: 2)
  - Page 3, Table 1, Row 5: "I RRM Peak Reverse Recovery Current - 141 - A"
  - Page 5, Table 6, Row 0: "25 V =-5/+18V GS V =800V DS L=100μH 20 R G(ext) =5Ω E total )Jm 15 ( s so L g E off n ih 10 c tiw S E on 5 0 0 40 80 120 160 200 Drain-Source Current, I (A) DS"


### voltage_rating (Voltage Rating) - 9 rejected

**Rejected by**: `gate_voltage_not_rating` (matched_alias: `voltage`, count: 3)
  - Page 2, Table 1, Row 2: "V GS Gate-Source Voltage (dynamic) -10/+22 V"
  - Page 2, Table 2, Row 3: "I DSS Zero Gate Voltage Drain Current - - 150 μA V =1200V; V =0V DS GS"
  - Page 4, Table 6, Row 0: "600 V =20V DS 500 )A 400 ( SD I ,tn e T=175℃ rru 300 J C e c ru T J =25℃ o S 200 - n ia T=-55℃ rD J 100 0 0 2 4 6 8 10 12 Gate-Source Voltage, V (V) GS"

**Rejected by**: `too_broad_without_context` (matched_alias: `voltage`, count: 5)
  - Page 2, Table 2, Row 5: "V GS(th) Gate Threshold Voltage 2 - 4 V V =V ; I =30mA DS GS D"
  - Page 2, Table 2, Row 7: "V GS(on) Recommended Turn-on Voltage - 18 - V Static"
  - Page 2, Table 2, Row 8: "V GS(off) Recommended Turn-off Voltage - -5 -"

**Rejected by**: `isolation_voltage_not_rating` (matched_alias: `voltage`, count: 1)
  - Page 3, Table 2, Row 4: "V isol Case Isolation Voltage (DC; t=1min) 4.2 - - kV"


## 8. Candidate Examples by Field

*Each field shows up to 3 example candidates*

### voltage_rating (Voltage Rating)

Total: 11 candidates | Exact: 7 | Symbol: 4 | Fuzzy: 0
Warnings: possible_overmatching

**Page 1, Table 2, Row 2**
- matched_alias: `voltage`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_source_voltage
- confidence: 0.95
- source_text: "V DS Drain-Source Voltage 1200 V T =25C C"

**Page 2, Table 1, Row 1**
- matched_alias: `voltage`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_source_voltage
- confidence: 0.95
- source_text: "V DS Drain-Source Voltage 1200 V"

**Page 2, Table 2, Row 2**
- matched_alias: `voltage`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_breakdown_voltage
- confidence: 0.95
- source_text: "BV DS Drain-Source Breakdown Voltage 1200 - - V V =0V GS"


### current_rating (Current Rating)

Total: 10 candidates | Exact: 10 | Symbol: 0 | Fuzzy: 0
Warnings: possible_overmatching

**Page 1, Table 2, Row 3**
- matched_alias: `current`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_current
- confidence: 0.95
- source_text: "I D Drain Current (continuous) 300 A T =25C C"

**Page 1, Table 2, Row 8**
- matched_alias: `IC`
- match_type: exact
- match_policy: strict_rating
- accept_reason: strong_current_context
- confidence: 0.95
- source_text: "R DS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ V =18V; I =150A; T =25C GS D C"

**Page 2, Table 1, Row 3**
- matched_alias: `current`
- match_type: exact
- match_policy: strict_rating
- accept_reason: matched_drain_current
- confidence: 0.95
- source_text: "I D Drain Current (continuous; T =25C) C 300 A"


### qg (QG (Total Gate Charge))

Total: 8 candidates | Exact: 5 | Symbol: 3 | Fuzzy: 0

**Page 1, Table 2, Row 10**
- matched_alias: `total gate charge`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "Q G Total Gate Charge - 618 - nC V =800V; V =-5/+18V; I =150A; DD GS D T =25C C"

**Page 1, Table 2, Row 11**
- matched_alias: `QG`
- match_type: symbol
- match_policy: normal
- confidence: 0.85
- source_text: "Q GD Gate-Drain Charge - 147 -"

**Page 2, Table 2, Row 16**
- matched_alias: `QG`
- match_type: symbol
- match_policy: normal
- confidence: 0.85
- source_text: "Q GS Gate-Source Charge - 174 - nC V =800V; V =-5/+18V; I =150A DD GS D"


### junction_temperature (Junction Temperature)

Total: 6 candidates | Exact: 4 | Symbol: 2 | Fuzzy: 0

**Page 1, Table 2, Row 5**
- matched_alias: `junction temp`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "T J; MAX Junction Temperature 175 C"

**Page 1, Table 2, Row 13**
- matched_alias: `TJ`
- match_type: symbol
- match_policy: normal
- confidence: 0.85
- source_text: "Q RR Reverse Recovery Charge - 1839 - nC V =-5/+18V; I =150A; V =800V; GS F R R =5Ω; Load=50µH; T=25C G(ext) J"

**Page 2, Table 1, Row 7**
- matched_alias: `junction temp`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "T J; MAX Junction Temperature 175 C"


### eon (Eon (Turn-On Energy))

Total: 5 candidates | Exact: 1 | Symbol: 4 | Fuzzy: 0

**Page 1, Table 2, Row 8**
- matched_alias: `Eon`
- match_type: symbol
- match_policy: normal
- confidence: 0.85
- source_text: "R DS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ V =18V; I =150A; T =25C GS D C"

**Page 2, Table 2, Row 6**
- matched_alias: `Eon`
- match_type: symbol
- match_policy: normal
- confidence: 0.85
- source_text: "R DS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ V =18V; I =150A GS D"

**Page 2, Table 2, Row 14**
- matched_alias: `turn-on energy`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "E on Turn-on Energy - 7.1 - mJ V =800V; V =-5/+18V; I =150A; DS GS D R =5Ω; Load=50µH G(ext)"


### rds_on_25c (RDS(on) @25°C)

Total: 3 candidates | Exact: 1 | Symbol: 2 | Fuzzy: 0

**Page 1, Table 2, Row 8**
- matched_alias: `RDS(on)`
- match_type: symbol
- match_policy: normal
- confidence: 0.85
- source_text: "R DS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ V =18V; I =150A; T =25C GS D C"

**Page 2, Table 2, Row 6**
- matched_alias: `RDS(on)`
- match_type: symbol
- match_policy: normal
- confidence: 0.85
- source_text: "R DS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ V =18V; I =150A GS D"

**Page 4, Table 2, Row 1**
- matched_alias: `on-resistance`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "Figure 2 Normalized On-Resistance vs. Temperature"


### rds_on_150c (RDS(on) @150°C)

Total: 3 candidates | Exact: 1 | Symbol: 2 | Fuzzy: 0

**Page 1, Table 2, Row 8**
- matched_alias: `RDS(on)`
- match_type: symbol
- match_policy: normal
- confidence: 0.85
- source_text: "R DS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ V =18V; I =150A; T =25C GS D C"

**Page 2, Table 2, Row 6**
- matched_alias: `RDS(on)`
- match_type: symbol
- match_policy: normal
- confidence: 0.85
- source_text: "R DS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ V =18V; I =150A GS D"

**Page 4, Table 2, Row 1**
- matched_alias: `on-resistance`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "Figure 2 Normalized On-Resistance vs. Temperature"


### crss (Crss)

Total: 3 candidates | Exact: 1 | Symbol: 2 | Fuzzy: 0

**Page 2, Table 2, Row 13**
- matched_alias: `reverse transfer capacitance`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "C rss Reverse Transfer Capacitance - 45 - pF"

**Page 5, Table 5, Row 0**
- matched_alias: `Crss`
- match_type: symbol
- match_policy: normal
- confidence: 0.85
- source_text: "100000 C 10000 ISS )F p ( e1000 c n a tic C a OSS p a C 100 C RSS 10 0 200 400 600 800 1000 1200 Drain-Source Voltage, V (V) DS"

**Page 5, Table 7, Row 3**
- matched_alias: `Crss`
- match_type: symbol
- match_policy: normal
- confidence: 0.85
- source_text: "C RSS"


### eoff (Eoff (Turn-Off Energy))

Total: 3 candidates | Exact: 1 | Symbol: 2 | Fuzzy: 0

**Page 2, Table 2, Row 15**
- matched_alias: `turn-off energy`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "E off Turn-off Energy - 7.9 -"

**Page 5, Table 6, Row 0**
- matched_alias: `Eoff`
- match_type: symbol
- match_policy: normal
- confidence: 0.85
- source_text: "25 V =-5/+18V GS V =800V DS L=100μH 20 R G(ext) =5Ω E total )Jm 15 ( s so L g E off n ih 10 c tiw S E on 5 0 0 40 80 120 160 200 Drain-Source Current, I (A) DS"

**Page 5, Table 8, Row 2**
- matched_alias: `Eoff`
- match_type: symbol
- match_policy: normal
- confidence: 0.85
- source_text: "E off"


### qgd (QGD (Gate-Drain Charge))

Total: 2 candidates | Exact: 2 | Symbol: 0 | Fuzzy: 0

**Page 1, Table 2, Row 11**
- matched_alias: `gate-drain charge`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "Q GD Gate-Drain Charge - 147 -"

**Page 2, Table 2, Row 17**
- matched_alias: `gate-drain charge`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "Q GD Gate-Drain Charge - 147 -"


### qrr (QRR (Reverse Recovery Charge))

Total: 2 candidates | Exact: 2 | Symbol: 0 | Fuzzy: 0

**Page 1, Table 2, Row 13**
- matched_alias: `reverse recovery charge`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "Q RR Reverse Recovery Charge - 1839 - nC V =-5/+18V; I =150A; V =800V; GS F R R =5Ω; Load=50µH; T=25C G(ext) J"

**Page 3, Table 1, Row 4**
- matched_alias: `reverse recovery charge`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "Q RR Reverse Recovery Charge - 1839 - nC"


### vgs_th (VGS(th))

Total: 2 candidates | Exact: 2 | Symbol: 0 | Fuzzy: 0

**Page 2, Table 2, Row 5**
- matched_alias: `gate threshold voltage`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "V GS(th) Gate Threshold Voltage 2 - 4 V V =V ; I =30mA DS GS D"

**Page 4, Table 5, Row 1**
- matched_alias: `threshold voltage`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "Figure 3 Threshold Voltage vs. Temperature"


### ciss (Ciss)

Total: 2 candidates | Exact: 1 | Symbol: 1 | Fuzzy: 0

**Page 2, Table 2, Row 11**
- matched_alias: `input capacitance`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "C iss Input Capacitance - 9.15 - nF V =1000V; f=1MHz; V =25mV DS AC"

**Page 5, Table 7, Row 0**
- matched_alias: `Ciss`
- match_type: symbol
- match_policy: normal
- confidence: 0.85
- source_text: "C ISS"


### trr (trr (Reverse Recovery Time))

Total: 2 candidates | Exact: 1 | Symbol: 1 | Fuzzy: 0

**Page 2, Table 2, Row 20**
- matched_alias: `trr`
- match_type: symbol
- match_policy: normal
- confidence: 0.85
- source_text: "t r Rise Time - 42 -"

**Page 3, Table 1, Row 3**
- matched_alias: `reverse recovery time`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "t RR Reverse Recovery Time - 96 - ns V =-5/+18V; I =150A; V =800V; GS F R R =5Ω; Load=50µH G(ext)"


### err (Err (Reverse Recovery Energy))

Total: 2 candidates | Exact: 0 | Symbol: 2 | Fuzzy: 0

**Page 4, Table 1, Row 0**
- matched_alias: `Err`
- match_type: symbol
- match_policy: normal
- confidence: 0.85
- source_text: "600 V GS =20V V GS =18V 500 )A V =16V ( 400 GS SD I ,tn e rru 300 C e c ru V GS =12V o S - 200 n ia rD 100 V =8V GS 0 0 2 4 6 8 Drain-Source Voltage, V (V) DS"

**Page 5, Table 1, Row 0**
- matched_alias: `Err`
- match_type: symbol
- match_policy: normal
- confidence: 0.85
- source_text: "-10 -9 -8 -7 -6 -5 -4 -3 -2 -1 0 0 V =-5V GS -100 V =-2V GS )A ( SD -200 I ,tn V =0V GS e rru C -300 e c ru o S n - -400 ia rD -500 -600 Drain-Source Voltage, V (V) DS"


### part_number (Part Number)

Total: 1 candidates | Exact: 1 | Symbol: 0 | Fuzzy: 0

**Page 1, Table 1, Row 2**
- matched_alias: `type`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "Package Type ME3"


### module_type (Module Type)

Total: 1 candidates | Exact: 1 | Symbol: 0 | Fuzzy: 0

**Page 1, Table 1, Row 2**
- matched_alias: `package`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "Package Type ME3"


### rth_jh (Rth JH (Junction-to-Heat sink))

Total: 1 candidates | Exact: 0 | Symbol: 1 | Fuzzy: 0

**Page 2, Table 1, Row 8**
- matched_alias: `Rth JH`
- match_type: symbol
- match_policy: normal
- confidence: 0.85
- source_text: "R th Jh Thermal Resistance, Junction-to-Heatsink 0.12 C/W"


### coss (Coss)

Total: 1 candidates | Exact: 1 | Symbol: 0 | Fuzzy: 0

**Page 2, Table 2, Row 12**
- matched_alias: `output capacitance`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "C oss Output Capacitance - 0.29 -"


### qgs (QGS (Gate-Source Charge))

Total: 1 candidates | Exact: 1 | Symbol: 0 | Fuzzy: 0

**Page 2, Table 2, Row 16**
- matched_alias: `gate-source charge`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "Q GS Gate-Source Charge - 174 - nC V =800V; V =-5/+18V; I =150A DD GS D"


### irrm (IRRM (Reverse Recovery Current))

Total: 1 candidates | Exact: 1 | Symbol: 0 | Fuzzy: 0

**Page 3, Table 1, Row 5**
- matched_alias: `peak reverse recovery current`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "I RRM Peak Reverse Recovery Current - 141 - A"


### lstray (Lstray (Stray Inductance))

Total: 1 candidates | Exact: 1 | Symbol: 0 | Fuzzy: 0

**Page 3, Table 2, Row 1**
- matched_alias: `stray inductance`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "L Stray Stray Inductance - 20 - nH"


### weight (Weight)

Total: 1 candidates | Exact: 1 | Symbol: 0 | Fuzzy: 0

**Page 3, Table 2, Row 2**
- matched_alias: `weight`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "W Weight - 340 - g"


### isol (Visol (Isolation Voltage))

Total: 1 candidates | Exact: 1 | Symbol: 0 | Fuzzy: 0

**Page 3, Table 2, Row 4**
- matched_alias: `isolation voltage`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "V isol Case Isolation Voltage (DC; t=1min) 4.2 - - kV"


### clearance_tt (Clearance T-T (Terminal to Terminal))

Total: 1 candidates | Exact: 1 | Symbol: 0 | Fuzzy: 0

**Page 3, Table 2, Row 5**
- matched_alias: `clearance`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "- Clearance Distance - 11 - mm Terminal to Terminal"


### clearance_tb (Clearance T-B (Terminal to Baseplate))

Total: 1 candidates | Exact: 1 | Symbol: 0 | Fuzzy: 0

**Page 3, Table 2, Row 5**
- matched_alias: `clearance`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "- Clearance Distance - 11 - mm Terminal to Terminal"


### creepage_tt (Creepage T-T (Terminal to Terminal))

Total: 1 candidates | Exact: 1 | Symbol: 0 | Fuzzy: 0

**Page 3, Table 2, Row 7**
- matched_alias: `creepage`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "- Creepage Distance - 23 - mm Terminal to Terminal"


### creepage_tb (Creepage T-B (Terminal to Baseplate))

Total: 1 candidates | Exact: 1 | Symbol: 0 | Fuzzy: 0

**Page 3, Table 2, Row 7**
- matched_alias: `creepage`
- match_type: exact
- match_policy: normal
- confidence: 0.95
- source_text: "- Creepage Distance - 23 - mm Terminal to Terminal"


