# AI Parameter Review Summary

**Document**: ASC300N1200ME3.pdf  
**Document ID**: f384879d1200  
**Review Date**: 2026-07-16  
**Overall Verdict**: **needs_repair**

---

## Overview

| Metric | Count |
|--------|-------|
| Total Fields Reviewed | 30 |
| Correct | 17 |
| Needs Repair | 13 |
| Critical Errors | 5 |

---

## Verdict Distribution

| Verdict | Count | Description |
|---------|--------|-------------|
| correct | 17 | Selection is correct |
| wrong_candidate | 5 | Wrong source row selected |
| condition_error | 2 | Condition missing or wrong |
| missing | 3 | No valid candidate found |
| uncertain | 2 | Cannot determine |
| unit_error | 1 | Unit mismatch |

---

## Severity Distribution

| Severity | Count | Fields |
|---------|-------|--------|
| critical | 5 | part_number, module_type, rds_on_150c, qg, junction_temperature |
| high | 2 | ciss, rth_jc |
| medium | 6 | manufacturer, eon, eoff, err, isol, clearance_tt |
| low | 17 | All others |

---

## Critical/High Severity Issues

### Critical Errors (5)

1. **part_number** - Wrong candidate
   - Selected value=3.0 from "Package Type ME3"
   - Should be "ASC300N1200ME3"
   - Parser incorrectly extracted numeric 3.0 from "ME3"

2. **module_type** - Wrong candidate
   - Selected value=3.0 from "Package Type ME3"
   - Should be "ME3"
   - Same error as part_number

3. **rds_on_150c** - Wrong candidate
   - Selected the SAME row as rds_on_25c (TC=25°C)
   - Should select RDS(on) @150°C row, not @25°C
   - Both selections have identical source_text confirming wrong复用

4. **qg** - Wrong candidate
   - Selected QGD (Gate-Drain Charge = 147 nC) instead of QG Total
   - Should select "QG Total Gate Charge - 618 nC"
   - QG = QGS + QGD, so 147 nC is only a component

5. **junction_temperature** - Wrong candidate
   - Selected value=1839°C from QRR row!
   - Should be 175°C from "TJ; MAX Junction Temperature" row
   - **Dangerous error**: 1839°C is not a valid temperature; this is QRR value (1839 nC)

### High Severity Issues (2)

6. **ciss** - Unit error
   - Source shows "9.15 nF" but selected unit is "pF"
   - Possible unit mismatch between value column and unit column

7. **rth_jc** - Missing
   - All candidates blocked or failed
   - No valid thermal resistance value found

---

## Suggested Action Distribution

| Action | Count | Fields |
|--------|-------|--------|
| keep | 16 | voltage_rating, current_rating, rds_on_25c, vgs_th, coss, crss, qgs, qgd, trr, irrm, rth_jh, lstray, weight, clearance_tt, creepage_tt, creepage_tb |
| replace_selected_candidate | 3 | module_type, qg, junction_temperature |
| mark_missing | 4 | manufacturer, part_number, err, rth_jc |
| downgrade_to_review | 4 | ciss, eoff, isol, clearance_tt |
| add_warning | 2 | eon, qrr |
| block_candidate | 1 | rds_on_150c |

---

## Most Important 5 Problems to Fix

### 1. junction_temperature is catastrophically wrong
- Currently: 1839°C (actually QRR value 1839 nC)
- Should be: 175°C
- Impact: HIGH - Would cause dangerous thermal miscalculations
- Fix: Replace with "TJ; MAX Junction Temperature 175 °C" candidate

### 2. part_number and module_type both wrong
- Currently: 3.0 (numeric)
- Should be: "ASC300N1200ME3" and "ME3"
- Impact: HIGH - Product identification completely wrong
- Fix: These should come from PDF header, not from "Package Type" table row

### 3. rds_on_150c incorrectly复用了 rds_on_25c data
- Currently: Same source as rds_on_25c (TC=25°C)
- Should be: RDS(on) measured at TC=150°C
- Impact: HIGH - Missing high-temperature data
- Fix: Mark as missing/blocked if no 150°C data exists in PDF

### 4. qg confused with qgd
- Currently: 147 nC (QGD, component charge)
- Should be: 618 nC (QG Total)
- Impact: HIGH - Total gate charge is 4x higher than selected
- Fix: Select "QG Total Gate Charge - 618 nC" instead

### 5. ciss unit mismatch
- Currently: 9.15 pF (but source says nF)
- Impact: MEDIUM - 1000x error if unit is wrong
- Fix: Verify unit from table column header

---

## Recommendation: Enter repair_selection.py?

**Yes, enter repair_selection.py** to fix the critical errors.

### Reasons:
1. 5 critical errors found that would cause wrong technical decisions
2. junction_temperature error (1839°C) is especially dangerous
3. qg wrong_candidate (4x error in gate charge) would affect driver design
4. part_number/module_type errors would cause wrong product identification

### Suggested Repair Order:
1. First: Fix junction_temperature (most dangerous)
2. Second: Fix qg (significant magnitude error)
3. Third: Fix rds_on_150c (mark as missing if no 150°C data)
4. Fourth: Fix part_number/module_type (product ID)
5. Fifth: Investigate ciss unit mismatch

### Fields to Auto-Repair (3):
- junction_temperature: Replace with 175°C candidate
- qg: Replace with 618 nC QG Total candidate
- module_type: Mark as "ME3" from source_text

### Fields to Manual Review (7):
- part_number: Needs human to find actual part number in PDF
- rds_on_150c: May be missing from PDF
- ciss: Needs unit verification
- rth_jc: Needs manual search in thermal tables
- manufacturer: Not found
- err: Not found or missing from PDF

### Fields to Keep As-Is (16):
All others are correct and can be kept.

---

*Report generated by AI Parameter Review Agent*
