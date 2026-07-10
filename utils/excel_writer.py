"""
Excel Output Writer

Outputs 4 sheets:
    1. Final Comparison - Parameter | Unit | Part A | Part B | ...
    2. Review Needed - Parameters that need human review
    3. Raw Extracted Params - All extracted parameters with source
    4. Source Evidence - Raw source text for verification

Format:
    - Final Comparison: Data cells contain ONLY values, units in header
    - Each part is one column group
    - Units are in column header, not mixed with values
"""
