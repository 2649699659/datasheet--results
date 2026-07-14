# Excel QA Audit Report — Step 7.2

**Generated:** 2026-07-14
**Source:** `output/final_comparison.xlsx` + `output/selected_params_debug.json`
**Scope:** Step 7.2 post-fix correctness audit (field-specific final validation)

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

**Correctly absent:** rds_on_150c, eon, eoff, junction_temperature, err, current_rating, voltage_rating, clearance_tb, creepage_tb ✅

---

## 3. RDS(on) Temperature Condition Check (Step 7.2)

### rds_on_25c ✅ CORRECTLY IN FINAL

| Check | Result |
|-------|--------|
| Status | **final_candidate** (score=88) |
| Temperature condition | Contains "25°C" in source_text ✅ |
| Source text | "R DS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ V =18V; I =150A; T =25°C" |
| Validation | Passes `_validate_field_specific_final_candidate()` ✅ |

**Unicode fix note:** The PDF uses U+F0B0 (CJK compatibility) degree character, not U+00B0. The Step 7.2 fix normalizes ALL non-ASCII characters from the temperature pattern, correctly detecting "25c" in the normalized text.

### rds_on_150c ✅ CORRECTLY DEMOTED TO REVIEW_NEEDED

| Check | Result |
|-------|--------|
| Status | **review_needed** (score=88) |
| Block reason | `rds_on_150c_missing_150c_temperature_condition` |
| Source text | "R DS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ V =18V; I =150A; T =25°C" |
| Problem | Source text only has "25°C", no "150°C" anywhere ✅ |
| Validation | Correctly blocked from Final by `_validate_field_specific_final_candidate()` ✅ |

**Conclusion:** rds_on_150c correctly demoted. The PDF does not contain a 150°C RDS(on) measurement. No 150°C data row exists for RDS(on) in this datasheet.

---

## 4. Eon / Eoff / Err Check (Step 7.2)

### eon ✅ CORRECTLY DEMOTED TO REVIEW_NEEDED

| Check | Result |
|-------|--------|
| Status | **review_needed** (score=-17) |
| Block reason | `energy_field_unit_missing_or_wrong; eon_selected_rds_on_row_instead_of_energy_row` |
| Selected source text | "R DS(on) Static Drain-Source on Resistance - 5.3 6.7 mΩ V =18V; I =150A; T =25°C" |
| Problem 1 | Selected_param unit is EMPTY — not an energy unit ✅ |
| Problem 2 | Selected_param source_text is RDS(on) row, NOT Eon row ✅ |
| Correct value | 7.1 mJ exists in `review_params[2]` (alternative_review) ✅ |
| Validation | Blocked from Final by `_validate_field_specific_final_candidate()` ✅ |

**Conclusion:** eon correctly demoted. The selector chose the wrong row (RDS(on) instead of Eon). The correct Eon value (7.1 mJ) is available in review_params.

### eoff ✅ CORRECTLY DEMOTED TO REVIEW_NEEDED

| Check | Result |
|-------|--------|
| Status | **review_needed** (score=-117) |
| Block reason | `parse_status=unsafe not clean enough for final` |
| Selected source text | "E off Turn-off Energy - 7.9 -" (trailing dash = unit not captured) |
| Problem | unit is EMPTY. Turn-off energy should have unit like mJ ✅ |
| Additional check | `_validate_field_specific_final_candidate()` also checks energy unit ✅ |
| Validation | Correctly blocked by parse_status gate + field-specific check ✅ |

**Conclusion:** eoff correctly demoted. Unit not captured from source.

### err ✅ CORRECTLY DEMOTED TO REVIEW_NEEDED

| Check | Result |
|-------|--------|
| Status | **review_needed** (score=-117) |
| Block reason | `parse_status=unsafe not clean enough for final` |
| Selected source text | "600 V GS =20V V GS =18V 500..." (garbled figure text, page 4) |
| Problem | Source is a figure/cross-section chart, not a parameter table ✅ |
| Value | 600.0 — but source is a chart axis/figure text ✅ |
| Additional check | `_validate_field_specific_final_candidate()` also rejects figure/axis sources ✅ |

**Conclusion:** err correctly demoted. Source is figure text, not a formal parameter specification.

---

## 5. junction_temperature Check (Step 7.2)

| Check | Result |
|-------|--------|
| Status | **review_needed** (score=-7) |
| Block reason | `junction_temperature_from_figure_axis_not_table_row` |
| Selected source text | "2 1.8 1.6... Junction Temperature, T (°C) J" (page 4 figure axis) |
| Value | min=0.0, max=50.0, unit=°C |
| Problem | Source is a figure axis/demperature derating curve, not a table specification row ✅ |
| Validation | Correctly blocked by `_validate_field_specific_final_candidate()` ✅ |

**Conclusion:** junction_temperature correctly demoted. The selected value appears to come from a figure temperature axis, not a formal specification table.

---

## 6. VGS(th) Check ✅

| Field | Value | Unit | Page | Status |
|-------|-------|------|------|--------|
| VGS(th) | 2.0 ~ 4.0 | V | 2 | ✅ CORRECT |

- min=2.0, max=4.0 ✅
- Displayed as "2.0 ~ 4.0" (not truncated) ✅
- original_unit=V ✅
- source_page=2 ✅
- No figure rows used ✅
- Field-specific validation passed (no temperature or unit rules for vgs_th) ✅

---

## 7. current_rating / voltage_rating Check

✅ Both are in **Review Needed only** (not in Final Comparison):

| Field | Selected Value | Unit | Sheet | Status |
|-------|---------------|------|-------|--------|
| current_rating | 25.0 | A | Review Needed | ✅ |
| voltage_rating | min=1200.0 | V | Review Needed | ✅ |

- Final Comparison: does NOT contain current_rating or voltage_rating ✅
- Both are in HIGH_RISK_FIELDS, so correctly routed to review_needed by `_classify_field()` ✅
- Blocked sheet: does NOT contain current_rating or voltage_rating ✅

---

## 8. clearance_tb / creepage_tb Check

✅ Both are in **Blocked only** (not in Final Comparison):

| Field ID | Label | Block Reason | Value | Unit | Sheet |
|----------|-------|-------------|-------|------|-------|
| clearance_tb | Clearance T-B | condition_type_mismatch_tt_vs_tb | 11.0 | mm | Blocked ✅ |
| creepage_tb | Creepage T-B | condition_type_mismatch_tt_vs_tb | 23.0 | mm | Blocked ✅ |

- condition says "Terminal to Terminal" but field requires "Terminal to Baseplate" ✅
- clearance_tt and creepage_tt are in Review Needed (correct — T-T conditions are valid for those) ✅
- Field ID format: `clearance_tb`, `creepage_tb` — underscores preserved ✅

---

## 9. Source Evidence Completeness

| Source | Count | Status |
|--------|-------|--------|
| Final Comparison (final_candidate) | 5 | ✅ |
| Review Needed (selected only) | 21 | ✅ |
| Blocked (selected only) | 2 | ✅ |
| **Total unique field_ids** | **28** | ✅ |
| **Source Evidence rows** | **28** | ✅ |

**By status breakdown in Source Evidence:**
- final_candidate: 5 ✅
- review_needed: 21 ✅
- blocked: 2 ✅

**Conclusion:** Source Evidence is **COMPLETE** — all 28 unique field_ids covered.

---

## 10. Field ID Format Check

**Checked across:** Review Needed (74 rows), Blocked (2 rows), Source Evidence (28 rows)

✅ **No underscore-loss issues found.** All field IDs correctly preserved:

| Field ID | Found in |
|----------|----------|
| `current_rating` ✅ | Review Needed, Source Evidence |
| `voltage_rating` ✅ | Review Needed, Source Evidence |
| `clearance_tb` ✅ | Blocked, Source Evidence |
| `creepage_tb` ✅ | Blocked, Source Evidence |
| `junction_temperature` ✅ | Review Needed, Source Evidence |
| `rth_jh` ✅ | Source Evidence |
| `rds_on_25c` ✅ | Final Comparison, Source Evidence |
| `rds_on_150c` ✅ | Review Needed, Source Evidence |
| `clearance_tt` ✅ | Review Needed, Source Evidence |
| `creepage_tt` ✅ | Review Needed, Source Evidence |
| `part_number` ✅ | Review Needed, Source Evidence |
| `module_type` ✅ | Review Needed, Source Evidence |
| `vgs_th` ✅ | Final Comparison, Source Evidence |

**Excel Writer:** Field IDs are correctly written as-is (e.g., "current_rating" not "currentrating") ✅

---

## 11. Final Summary — Changes from Step 7.1 to Step 7.2

| Field | Step 7.1 Status | Step 7.2 Status | Change |
|-------|-----------------|-----------------|--------|
| rds_on_25c | ❌ WRONG (was final_candidate but should be) | ✅ CORRECT (final_candidate with right row) | **FIXED** — Unicode degree normalization |
| rds_on_150c | ❌ FALSE POSITIVE (same row as rds_on_25c) | ✅ DEMOTED (review_needed) | **FIXED** — temperature condition check |
| eon | ❌ WRONG ROW (RDS(on) selected) | ✅ DEMOTED (review_needed) | **FIXED** — energy unit + source check |
| eoff | ⚠️ EMPTY UNIT | ✅ DEMOTED (review_needed) | **STAYS DEMOTED** — parse_status=unsafe |
| junction_temperature | ⚠️ FROM FIGURE AXIS | ✅ DEMOTED (review_needed) | **FIXED** — figure/axis rejection |
| err | ⚠️ FROM FIGURE AXIS | ✅ DEMOTED (review_needed) | **FIXED** — parse_status=unsafe + figure rejection |
| vgs_th | ✅ CORRECT | ✅ CORRECT | **UNCHANGED** |
| trr | ✅ CORRECT | ✅ CORRECT | **UNCHANGED** |
| lstray | ✅ CORRECT | ✅ CORRECT | **UNCHANGED** |
| weight | ✅ CORRECT | ✅ CORRECT | **UNCHANGED** |

---

## 12. Validation Results

| Command | Result |
|---------|--------|
| `python3 main.py --validate-config` | ✅ PASS (30 fields, 0 errors) |
| `python3 main.py --test-units` | ✅ PASS (14/14 tests) |
| `python3 main.py --pdf ... --output final_comparison.xlsx` | ✅ PASS |

---

## 13. Readiness for Human Review

**Final Comparison (5 fields):** ✅ Ready for human review
- These 5 fields have clean source evidence and pass all field-specific checks

**Review Needed (21 fields + 74 rows including alternatives):** ⚠️ Human review required
- current_rating: Need to confirm correct rating value (25A vs 480A vs 75A vs 300A?)
- voltage_rating: Need to confirm BV_DSS = 1200V is the correct rating
- rds_on_150c: No 150°C data in PDF — human should confirm if 150°C spec exists elsewhere
- eon: Correct value (7.1 mJ) available in alternative_review — human should select
- eoff: Unit not captured — human should find correct unit (likely mJ)
- junction_temperature: Figure axis value — human should find actual Tj spec
- err: Figure text value — human should find actual Err spec

**Blocked (2 fields):** ✅ Clear — condition mismatch, no human action needed for unblocking

**Recommendation:** ✅ **Ready for human review**, with the 5 Final Comparison fields being the primary deliverable and the 21 Review Needed fields requiring human judgment to finalize.
