# Excel QA Audit - Step 7.4
Generated: 2026-07-14 14:41:16
## Overview
- **File**: output/final_comparison.xlsx
- **Step**: 7.4 - Condition Display in All Sheets

## Final Comparison Sheet
| Parameter | Unit | Value | Condition | Page |
|-----------|------|-------|-----------|------|
| RDS(on) @25°C | mΩ | typ=5.3; max=6.7 | T=25; V=18; I=150 | 1 |
| VGS(th) | V | 2.0 ~ 4.0 | VDS=VGS; I=30 | 2 |
| trr (Reverse Recovery Time) | ns | typ=96.0 | Load=50; R=5; V=800; I=150 | 3 |
| Lstray (Stray Inductance) | nH | typ=20.0 | (none) | 3 |
| Weight | g | typ=340.0 | (none) | 3 |

## Review Needed Sheet - Condition Summary
| Field ID | Selected Value | Condition |
|----------|---------------|----------|
| eon | 7.1 mJ | Load=50; R=5; V=800; I=150 |
| eoff | 7.9 mJ | (none) |
| rds_on_150c | typ=5.3; max=6.7 mΩ | T=25; V=18; I=150 |
| current_rating | 25.0 A | T=25 |
| voltage_rating | min=1200.0 V | V=0 |

## Blocked Sheet
| Field ID | Block Reason | Condition |
|----------|--------------|----------|
| clearance_tb | condition_type_mismatch_tt_vs_tb | Terminal to Terminal |
| creepage_tb | condition_type_mismatch_tt_vs_tb | Terminal to Terminal |

## Condition Extraction - Verified Patterns
- **Temperature**: T=25, TC=25, TJ=25 → extracted from 'T=25°C' source
- **Voltage**: VDS=VGS → extracted for VGS(th) condition
- **Gate resistance**: RG=5, R=5 → extracted from 'RG(ext)=5Ω' and 'R=5Ω'
- **Load**: Load=50 → extracted from 'Load=50µH'
- **Voltage general**: V=18, V=800 → extracted from 'V=18V' and 'V=800V'
- **Current**: I=150, I=30 → extracted from 'I=150A' and 'I=30mA'
- **Terminal-to-Terminal**: 'Terminal to Terminal' → static keyword match
