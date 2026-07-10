"""
Final Value Selection Layer

This is the MOST CRITICAL module.

Responsibilities:
    1. Align extracted params with target_fields.yaml
    2. Select final values (prefer typ, handle min/max)
    3. Unit validation
    4. Conflict detection
    5. Generate data structures for output sheets:
        - Final Comparison
        - Review Needed
        - Raw Extracted Params
        - Source Evidence

Final Selection Principles:
    1. Final Comparison only contains certain values
    2. Every Final value must have source_text or source evidence
    3. Values without source CANNOT enter Final Comparison
    4. Multiple conflicting candidates -> Final stays empty, enters Review Needed
    5. Uncertain unit -> Review Needed
    6. Conditions matter - do not mix, e.g., RDS(on) @25°C vs @150°C are separate
    7. Clearance/Creepage must distinguish T-T and T-B
    8. Do NOT estimate values not in PDF
"""
