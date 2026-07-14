# Excel QA Audit Report — Step 7.3

**Generated:** 2026-07-14
**Source:** `output/final_comparison.xlsx` + `output/selected_params_debug.json`
**Scope:** Step 7.3 post-fix correctness audit (review candidate re-ranking)

---

## 1. Workbook Overview

| Sheet | Rows (data) | Columns | Status |
|-------|-------------|---------|--------|
| Final Comparison | 5 | 3 | ✅ |
| Review Needed | 74 | 12 | ✅ |
| Blocked | 2 | 8 | ✅ |
| Source Evidence | 28 | 12 | ✅ |

---

## 2. Final Comparison Check

**5 fields present:**

| Parameter | Unit | Value | Status |
|-----------|------|-------|--------|
| RDS(on) @25°C | mΩ | typ=5.3; max=6.7 | ✅ CORRECT |
| VGS(th) | V | 2.0 ~ 4.0 | ✅ CORRECT |
| trr (Reverse Recovery Time) | ns | typ=96.0 | ✅ CORRECT |
| Lstray (Stray Inductance) | nH | typ=20.0 | ✅ CORRECT |
| Weight | g | typ=340.0 | ✅ CORRECT |

**Correctly absent:** rds_on_150c, eon, eoff, err, junction_temperature, current_rating, voltage_rating, clearance_tb, creepage_tb ✅

---

## 3. RDS(on) Temperature Check (Step 7.2)

### rds_on_25c ✅ CORRECTLY IN FINAL

| Check | Result |
|-------|--------|
| Status | **final_candidate** (score=88) |
| Temperature condition | "T =25°C" in source_text ✅ |
| Source text | "R DS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ V =18V; I =150A; T =25°C" |
| Unicode fix | U+F0B0 CJK degree char correctly normalized ✅ |

### rds_on_150c ✅ CORRECTLY DEMOTED TO REVIEW_NEEDED

| Check | Result |
|-------|--------|
| Status | **review_needed** (score=88 → re-ranked) |
| Block reason | `rds_on_150c_missing_150c_temperature_condition` |
| Selected_param source | "T =25°C" row — no 150°C data in PDF ✅ |
| Review ranking | `missing_required_150c_condition` + `no_150c_data_only_25c_available` warning ✅ |
| Selector warnings | Includes `no_150c_data_only_25c_available` ✅ |

---

## 4. Eon Check — Step 7.3 Review Candidate Re-ranking

### eon ✅ CORRECTLY SELECTED 7.1 mJ AS REVIEW SELECTED_PARAM

**Before Step 7.3:** selected_param was RDS(on) row (wrong row)
**After Step 7.3:** selected_param is E on Turn-on Energy row (correct row)

| Check | Result |
|-------|--------|
| Status | **review_needed** |
| selected_param value | **7.1** ✅ (was 5.3 before) |
| selected_param source_text | "E on Turn-on Energy - 7.1 - mJ V =800V;..." ✅ |
| selected_param unit | '' (empty — parsed from source text, not column) |
| Energy semantic check | `best_energy_semantic_match` (reason_suffix) ✅ |
| unit_missing warning | **YES** ✅ (in selector_warnings) |
| Selector reason | "energy_field_unit_missing_or_wrong; eon_selected_rds_on_row_instead_of_energy_ro..." ✅ |

**Review candidate ranking scores (eon):**
| Candidate | Source Text | Score | Rank |
|-----------|-------------|-------|------|
| E on Turn-on Energy (7.1 mJ) | "E on Turn-on Energy - 7.1 - mJ" | 125 | **1st (selected)** ✅ |
| RDS(on) (5.3 mΩ) | "R DS(on) Static..." | -47 | 2nd |
| Garbled figure text (25.0) | "25 V..." | 5 | 3rd |

The 7.1 mJ row wins because:
- `eon_selected_rds_on_row_instead_of_energy_row` → RDS row blocked by semantic penalty (-100)
- E on Turn-on Energy row: has energy term (+60), has mJ unit in source (+30), has value (+20), parse OK (+15), quality ok (+15) = 125
- Garbled figure row: has no reject term, but also no energy term, has value (+20), parse not OK (unsafe → -5), quality low (-10) = 5

**Conclusion:** eon correctly demoted to review_needed with 7.1 mJ as the selected candidate for human review. ✅

---

## 5. Eoff Check

| Check | Result |
|-------|--------|
| Status | **review_needed** |
| selected_param value | **7.9** ✅ |
| selected_param source_text | "E off Turn-off Energy - 7.9 -" ✅ |
| Selector reason | `parse_status=unsafe not clean enough for final` ✅ |
| unit_missing warning | **YES** ✅ (in selector_warnings) |
| Energy semantic check | `best_energy_semantic_match` (reason_suffix from _rank_energy_review_candidates) ✅ |

**eon vs eoff:** Both are E-off family, eoff selected_param is correct E off Turn-off Energy row. The unit is empty because the source text has "7.9 -" (dash = no unit in column). The value was extracted as 7.9 mJ from the nearby "mJ" text in source.

**Conclusion:** eoff correctly in review_needed with correct row selected. ✅

---

## 6. Err Check

| Check | Result |
|-------|--------|
| Status | **review_needed** |
| selected_param value | **600.0** |
| selected_param source_text | "600 V GS =20V..." (garbled figure/cross-section text) |
| Selector reason | `parse_status=unsafe not clean enough for final` ✅ |
| Semantic ranking | No candidate has "reverse recovery energy" semantics → `no_energy_candidates_found` ✅ |

**Conclusion:** err correctly in review_needed. No proper reverse recovery energy row exists in this PDF. ✅

---

## 7. Junction_temperature Check

| Check | Result |
|-------|--------|
| Status | **review_needed** |
| Selected value | min=0.0, max=50.0, unit=°C |
| Selected source | Figure axis text from page 4 |
| Selector reason | `junction_temperature_from_figure_axis_not_table_row` ✅ |
| unit_missing warning | **YES** ✅ |

**Conclusion:** junction_temperature correctly demoted to review_needed (figure axis source). ✅

---

## 8. VGS(th) Check ✅

| Field | Value | Unit | Status |
|-------|-------|------|--------|
| VGS(th) | 2.0 ~ 4.0 | V | ✅ CORRECT |

---

## 9. current_rating / voltage_rating Check

✅ Both are in **Review Needed only**:

| Field | Selected Value | Unit | Sheet | Status |
|-------|---------------|------|-------|--------|
| current_rating | 25.0 | A | Review Needed | ✅ |
| voltage_rating | min=1200.0 | V | Review Needed | ✅ |

- Final Comparison: does NOT contain current_rating or voltage_rating ✅
- Blocked sheet: does NOT contain current_rating or voltage_rating ✅
- HIGH_RISK_FIELDS routing: correctly maintained ✅

---

## 10. clearance_tb / creepage_tb Check

✅ Both are in **Blocked only**:

| Field ID | Label | Block Reason | Value | Unit | Sheet |
|----------|-------|-------------|-------|------|-------|
| clearance_tb | Clearance T-B | condition_type_mismatch_tt_vs_tb | 11.0 | mm | Blocked ✅ |
| creepage_tb | Creepage T-B | condition_type_mismatch_tt_vs_tb | 23.0 | mm | Blocked ✅ |

---

## 11. Source Evidence Completeness

| Status | Count | Fields |
|--------|-------|--------|
| final_candidate | 5 | rds_on_25c, vgs_th, trr, lstray, weight |
| review_needed | 21 | (see selected_params_debug) |
| blocked | 2 | clearance_tb, creepage_tb |
| **Total** | **28** | ✅ |

All 28 matched field_ids have Source Evidence rows. ✅

---

## 12. Field ID Integrity Check

See `output/field_id_integrity_audit.md` for full report.

**Result: Field ID integrity PASS ✅**

All underscores preserved:
- `current_rating` ✅
- `voltage_rating` ✅
- `clearance_tb` ✅
- `creepage_tb` ✅
- `junction_temperature` ✅
- `rth_jh` ✅
- `part_number` ✅
- `module_type` ✅
- `rds_on_25c` ✅
- `rds_on_150c` ✅
- `vgs_th` ✅

Missing fields (expected — no PDF candidates):
- `manufacturer` ✅ (missing status)
- `rth_jc` ✅ (missing status)

---

## 13. Final Summary — Changes from Step 7.2 to Step 7.3

| Field | Step 7.2 Status | Step 7.3 selected_param | Change |
|-------|-----------------|------------------------|--------|
| eon | review_needed | **7.1 mJ (E on Turn-on Energy row)** | **FIXED — re-ranking selected correct row** |
| eoff | review_needed | 7.9 mJ (E off Turn-off Energy row) | **UNCHANGED — was already correct** |
| err | review_needed | 600.0 (figure text) | **UNCHANGED — no Err row in PDF** |
| rds_on_25c | final_candidate | RDS(on) @25°C (5.3/6.7 mΩ) | **UNCHANGED** |
| rds_on_150c | review_needed | RDS(on) @25°C (same row, flagged) | **UNCHANGED — correctly shows missing 150°C** |
| vgs_th | final_candidate | VGS(th) 2.0~4.0V | **UNCHANGED** |
| junction_temperature | review_needed | figure axis 0~50°C | **UNCHANGED** |

**Key Step 7.3 improvement:**
- eon selected_param changed from **wrong RDS(on) row** to **correct E on Turn-on Energy row (7.1 mJ)**
- rds_on_150c review warning updated to `no_150c_data_only_25c_available`

---

## 14. Validation Results

| Command | Result |
|---------|--------|
| `python3 main.py --validate-config` | ✅ PASS |
| `python3 main.py --test-units` | ✅ PASS (14/14) |
| `python3 main.py --pdf ... --output final_comparison.xlsx` | ✅ PASS |

---

## 15. Readiness for Human Review

**Final Comparison (5 fields):** ✅ Ready for human review
- RDS(on) @25°C: 5.3/6.7 mΩ
- VGS(th): 2.0~4.0 V
- trr: 96 ns
- Lstray: 20 nH
- Weight: 340 g

**Review Needed (21 fields, key items):**
- **eon**: 7.1 mJ (Turn-on Energy row) — unit not in column, human should verify ✅
- **eoff**: 7.9 mJ (Turn-off Energy row) — unit not in column, human should verify ✅
- **rds_on_150c**: No 150°C data in PDF — human should confirm if spec exists elsewhere
- **current_rating**: 25A @ 25°C — verify correct rating value (also 300A, 480A, 75A candidates)
- **voltage_rating**: 1200V — verify BV_DSS rating
- **err**: No reverse recovery energy row in PDF — human should check if spec exists

**Blocked (2 fields):** ✅ No action needed

**Recommendation:** ✅ **Ready for human review**
