"""
Unit Converter Module

Provides lightweight unit conversion and normalization utilities.

Note: This is a skeleton implementation for future use.
Do NOT integrate with parser in this phase.

Supported conversions:
- pF <-> nF
- nF <-> μF
- nC <-> μC
- μJ <-> mJ
- mΩ <-> Ω
- K/W <-> °C/W (treated as equivalent)
"""

from typing import Optional, Tuple, Dict


# Supported unit conversion factors
# Key: (from_unit, to_unit) -> multiplier
SUPPORTED_CONVERSIONS: Dict[Tuple[str, str], float] = {
    # Capacitance
    ("pF", "nF"): 1e-3,      # 1 pF = 0.001 nF
    ("nF", "pF"): 1e3,        # 1 nF = 1000 pF
    ("nF", "μF"): 1e-3,      # 1 nF = 0.001 μF
    ("μF", "nF"): 1e3,        # 1 μF = 1000 nF
    ("pF", "μF"): 1e-6,      # 1 pF = 0.000001 μF
    ("μF", "pF"): 1e6,        # 1 μF = 1000000 pF
    
    # Charge
    ("nC", "μC"): 1e-3,      # 1 nC = 0.001 μC
    ("μC", "nC"): 1e3,        # 1 μC = 1000 nC
    ("pC", "nC"): 1e-3,      # 1 pC = 0.001 nC
    ("nC", "pC"): 1e3,        # 1 nC = 1000 pC
    ("pC", "μC"): 1e-6,      # 1 pC = 0.000001 μC
    ("μC", "pC"): 1e6,        # 1 μC = 1000000 pC
    
    # Energy
    ("μJ", "mJ"): 1e-3,      # 1 μJ = 0.001 mJ
    ("mJ", "μJ"): 1e3,        # 1 mJ = 1000 μJ
    ("nJ", "μJ"): 1e-3,      # 1 nJ = 0.001 μJ
    ("μJ", "nJ"): 1e3,        # 1 μJ = 1000 nJ
    ("nJ", "mJ"): 1e-6,      # 1 nJ = 0.000001 mJ
    ("mJ", "nJ"): 1e6,        # 1 mJ = 1000000 nJ
    
    # Resistance
    ("mΩ", "Ω"): 1e-3,       # 1 mΩ = 0.001 Ω
    ("Ω", "mΩ"): 1e3,         # 1 Ω = 1000 mΩ
    ("kΩ", "Ω"): 1e3,         # 1 kΩ = 1000 Ω
    ("Ω", "kΩ"): 1e-3,       # 1 Ω = 0.001 kΩ
    ("MΩ", "Ω"): 1e6,         # 1 MΩ = 1000000 Ω
    ("Ω", "MΩ"): 1e-6,       # 1 Ω = 0.000001 MΩ
    
    # Thermal Resistance
    # K/W and °C/W are equivalent (just different notation)
    # No conversion needed, treated as equivalent units
}

# Units that are equivalent for thermal resistance
THERMAL_RESISTANCE_EQUIVALENTS = {
    ("K/W", "°C/W"),
    ("°C/W", "K/W"),
}

# Unit normalization map (variant -> canonical)
UNIT_ALIASES: Dict[str, str] = {
    # Capacitance
    "uf": "μF",
    "uf": "μF",
    "pf": "pF",
    "nf": "nF",
    
    # Charge
    "uc": "μC",
    "uc": "μC",
    "nc": "nC",
    "pc": "pC",
    
    # Energy
    "uj": "μJ",
    "mj": "mJ",
    "nj": "nJ",
    
    # Resistance
    "ohm": "Ω",
    "ohms": "Ω",
    "mohm": "mΩ",
    "mohms": "mΩ",
    "kohm": "kΩ",
    "kohms": "kΩ",
    "megohm": "MΩ",
    "megohms": "MΩ",
    
    # Thermal resistance
    "degc/w": "°C/W",
    "degc_per_w": "°C/W",
    "k/w": "K/W",
    "k_per_w": "K/W",
    
    # Time
    "us": "μs",
    "mus": "μs",
    "ns": "ns",
    "ms": "ms",
    
    # Frequency
    "khz": "kHz",
    "mhz": "MHz",
    
    # Length
    "um": "μm",
    "micrometer": "μm",
    "microns": "μm",
}


def normalize_unit(unit: str) -> str:
    """
    Normalize unit string to canonical form.
    
    Handles common variations:
    - uC -> μC
    - uJ -> μJ
    - degC/W -> °C/W
    - ohm -> Ω
    - mOhm -> mΩ
    - etc.
    
    Args:
        unit: Raw unit string
        
    Returns:
        Normalized unit string
    """
    if not unit:
        return ""
    
    # Strip whitespace
    unit = unit.strip()
    
    # Check direct match first
    if unit in UNIT_ALIASES:
        return UNIT_ALIASES[unit]
    
    # Check case-insensitive match
    unit_lower = unit.lower()
    for alias, canonical in UNIT_ALIASES.items():
        if alias.lower() == unit_lower:
            return canonical
    
    # Return as-is if no normalization found
    return unit


def can_convert(from_unit: str, to_unit: str) -> bool:
    """
    Check if conversion between two units is supported.
    
    Args:
        from_unit: Source unit (will be normalized)
        to_unit: Target unit (will be normalized)
        
    Returns:
        True if conversion is supported, False otherwise
    """
    from_norm = normalize_unit(from_unit)
    to_norm = normalize_unit(to_unit)
    
    # Same unit - no conversion needed
    if from_norm == to_norm:
        return True
    
    # Check explicit conversions
    if (from_norm, to_norm) in SUPPORTED_CONVERSIONS:
        return True
    
    # Check thermal resistance equivalents
    if (from_norm, to_norm) in THERMAL_RESISTANCE_EQUIVALENTS:
        return True
    
    return False


def convert_value(value: float, from_unit: str, to_unit: str) -> Optional[float]:
    """
    Convert a value from one unit to another.
    
    Args:
        value: Numeric value to convert
        from_unit: Source unit
        to_unit: Target unit
        
    Returns:
        Converted value, or None if conversion not supported
        
    Raises:
        ValueError: If units are not convertible
    """
    from_norm = normalize_unit(from_unit)
    to_norm = normalize_unit(to_unit)
    
    # Same unit - no conversion needed
    if from_norm == to_norm:
        return value
    
    # Check thermal resistance equivalents (no numeric conversion needed)
    if (from_norm, to_norm) in THERMAL_RESISTANCE_EQUIVALENTS:
        return value
    
    # Check explicit conversions
    key = (from_norm, to_norm)
    if key in SUPPORTED_CONVERSIONS:
        return value * SUPPORTED_CONVERSIONS[key]
    
    # Conversion not supported
    return None


def get_conversion_factor(from_unit: str, to_unit: str) -> Optional[float]:
    """
    Get the conversion factor between two units.
    
    Args:
        from_unit: Source unit
        to_unit: Target unit
        
    Returns:
        Multiplication factor, or None if not convertible
    """
    from_norm = normalize_unit(from_unit)
    to_norm = normalize_unit(to_unit)
    
    if from_norm == to_norm:
        return 1.0
    
    if (from_norm, to_norm) in THERMAL_RESISTANCE_EQUIVALENTS:
        return 1.0
    
    return SUPPORTED_CONVERSIONS.get((from_norm, to_norm))


def test_conversions() -> Tuple[bool, list]:
    """
    Run a set of test conversions.
    
    Returns:
        (all_passed, list_of_results)
    """
    test_cases = [
        # (value, from_unit, to_unit, expected_result)
        (8500, "nC", "μC", 8.5),
        (8500, "μJ", "mJ", 8.5),
        (9150, "pF", "nF", 9.15),
        (5.3, "mΩ", "Ω", 0.0053),
        # Thermal resistance equivalents
        (1.0, "K/W", "°C/W", 1.0),
        (1.0, "°C/W", "K/W", 1.0),
        # Same unit
        (10, "mJ", "mJ", 10),
        # Unsupported conversion
        (100, "pF", "mJ", None),
    ]
    
    results = []
    all_passed = True
    
    for value, from_unit, to_unit, expected in test_cases:
        result = convert_value(value, from_unit, to_unit)
        
        if expected is None:
            # Expecting None (unsupported)
            passed = result is None
        else:
            # Expecting numeric value
            passed = result is not None and abs(result - expected) < 1e-9
        
        status = "✓" if passed else "✗"
        results.append(f"  {status} convert({value}, {from_unit}, {to_unit}) = {result} (expected: {expected})")
        
        if not passed:
            all_passed = False
    
    return all_passed, results
