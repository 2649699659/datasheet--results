# Excel Readiness Audit (Step 5.8)

## Summary

| Category | Count |
|----------|-------|
| ready_for_final | 0 |
| review_only | 22 |
| blocked | 6 |
| missing (no candidates) | 2 |
| TOTAL | 30 |

**Overall Status**: NOT READY

## ready_for_final

*No fields ready for final.*

## review_only

| Field ID | parse_quality | Issues |
|----------|---------------|--------|
| ciss | low, medium | no_reliable_header |
| coss | low | no_reliable_header |
| crss | low | no_reliable_header |
| eoff | low, medium | no_reliable_header |
| eon | low, medium | no_reliable_header |
| irrm | low | no_reliable_header |
| isol | low | no_reliable_header |
| junction_temperature | low, medium | no_reliable_header |
| lstray | medium | - |
| module_type | low, medium | no_reliable_header |
| part_number | low | no_reliable_header |
| qg | low, medium | no_reliable_header |
| qgd | low | no_reliable_header |
| qgs | low | no_reliable_header |
| qrr | low | no_reliable_header |
| rds_on_150c | low, medium | no_reliable_header |
| rds_on_25c | low, medium | no_reliable_header |
| rth_jc | medium | - |
| rth_jh | low | no_reliable_header |
| trr | low, medium | no_reliable_header |
| voltage_rating | low, medium | - |
| weight | medium | - |

## blocked

| Field ID | Count | Critical Issues |
|----------|-------|----------------|
| clearance_tb | 2 | condition_type_mismatch, condition_unclear |
| clearance_tt | 2 | condition_unclear |
| creepage_tb | 2 | condition_type_mismatch, condition_unclear |
| creepage_tt | 2 | condition_unclear |
| current_rating | 10 | ambiguous |
| vgs_th | 3 | partial_threshold_values |

## missing (no candidates)

| Field ID |
|----------|
| err |
| manufacturer |
