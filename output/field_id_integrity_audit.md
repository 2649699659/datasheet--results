# Field ID Integrity Audit — Step 7.3

**Generated:** 2026-07-14
**Source:** `config/target_fields.yaml`, `output/selected_params_debug.json`, `output/final_comparison.xlsx`

---

## Summary

| Check | Result |
|-------|--------|
| target_fields.yaml | 30 field_ids |
| selected_params_debug.json | 30 field_ids (all match yaml) |
| Excel Review Needed | 21 unique field_ids |
| Excel Blocked | 2 unique field_ids |
| Excel Source Evidence | 28 unique field_ids |
| **Field ID integrity** | **PASS** ✅ |

---

## Field ID Counts

| Source | Count |
|--------|-------|
| target_fields.yaml | 30 |
| selected_params_debug.json | 30 |
| Excel Review Needed (unique) | 21 |
| Excel Blocked (unique) | 2 |
| Excel Source Evidence (unique) | 28 |

**Missing from Excel** (expected — no candidates in PDF):
- `manufacturer` ✅ — missing status (not in PDF)
- `rth_jc` ✅ — missing status (not in PDF)

**Invalid field IDs** (in Excel but not in yaml): **NONE** ✅

---

## Special Field ID Check

| Field ID | In YAML | In JSON | In Excel | Status |
|----------|---------|---------|----------|--------|
| `current_rating` | ✅ | ✅ | ✅ | OK |
| `voltage_rating` | ✅ | ✅ | ✅ | OK |
| `clearance_tb` | ✅ | ✅ | ✅ | OK |
| `creepage_tb` | ✅ | ✅ | ✅ | OK |
| `junction_temperature` | ✅ | ✅ | ✅ | OK |
| `rth_jh` | ✅ | ✅ | ✅ | OK |
| `part_number` | ✅ | ✅ | ✅ | OK |
| `module_type` | ✅ | ✅ | ✅ | OK |
| `rds_on_25c` | ✅ | ✅ | ✅ | OK |
| `rds_on_150c` | ✅ | ✅ | ✅ | OK |
| `vgs_th` | ✅ | ✅ | ✅ | OK |

**All underscores preserved correctly in all sources.** The previous report's markdown display issue (underscores appearing as spaces in plain text) was a rendering artifact only — `repr()` of the actual cell values confirms all field IDs are intact.

---

## Verification Method

```python
# Verified using repr() to avoid markdown underscore display issues:
repr(ws.cell(row=r, column=2).value)
# e.g., 'current_rating' not currentrating
```

All field IDs verified via Python repr() output, not markdown rendering.

---

## Conclusion

**Field ID integrity: PASS ✅**

No field IDs were lost or modified during:
- Final Selector processing
- JSON serialization
- Excel Writer output

The 2 missing field IDs (`manufacturer`, `rth_jc`) are correctly absent — they have no candidate data in the source PDF and are in `missing` status as expected.
