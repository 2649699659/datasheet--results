"""
Condition String Parser

Parses condition strings like:
    - "25°C", "150°C", "TJ=150°C"
    - "TC=25°C", "TJ=125°C"
    - "VDS=600V", "VGS=15V", "ID=20A"
    - "f=1MHz"
    - "Terminal to Terminal", "T-T"
    - "Terminal to Baseplate", "T-B"

Functions:
    - parse_condition(condition_str) -> Condition
    - extract_temperature(condition_str) -> str
    - extract_voltage(condition_str) -> str
    - extract_current(condition_str) -> str
    - extract_frequency(condition_str) -> str
    - extract_clearance_type(condition_str) -> str
    - is_tt(condition_str) -> bool
    - is_tb(condition_str) -> bool
"""
