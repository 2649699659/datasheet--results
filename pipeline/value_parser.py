"""
Value Parser for Datasheet Extractor

Step 5.5: Quality fixes and safety guards.

Architecture:
    - pipeline/parser.py: Candidate row matching
    - pipeline/value_parser.py: Value extraction from active candidates

Quality principles:
    - Conservative column detection (only trust headers)
    - Unit sanity check per field
    - High-risk field special handling
    - Parse quality flags
"""

import re
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field

from pipeline.models import RawExtractedParam, ParamStatus, ExtractionMethod, UnitConversionStatus


# Unit patterns for extraction
# Unit patterns - LONGEST/MOST_SPECIFIC FIRST to avoid short-unit greedy matching
# Each entry: (pattern, normalized_unit)
UNIT_PATTERNS: List[Tuple[str, str]] = [
    # Thermal resistance (compound units - longest first)
    (r'°C/W\b', '°C/W'),
    (r'K/W\b', 'K/W'),
    # Ohm variants (compound first, then base)
    (r'mΩ\b', 'mΩ'),
    (r'kΩ\b', 'kΩ'),
    (r'MΩ\b', 'MΩ'),
    (r'Ω\b', 'Ω'),
    # Voltage variants
    (r'kV\b', 'kV'),
    (r'mV\b', 'mV'),
    (r'μV\b', 'μV'),
    (r'V\b', 'V'),
    # Current variants
    (r'mA\b', 'mA'),
    (r'μA\b', 'μA'),
    (r'uA\b', 'uA'),
    (r'A\b', 'A'),
    # Capacitance variants
    (r'nF\b', 'nF'),
    (r'pF\b', 'pF'),
    (r'μF\b', 'μF'),
    (r'uF\b', 'uF'),
    (r'F\b', 'F'),
    # Temperature (must be before C to avoid matching C in °C)
    (r'°C\b', '°C'),
    # Charge variants (C after °C to avoid conflict)
    (r'μC\b', 'μC'),
    (r'uC\b', 'uC'),
    (r'nC\b', 'nC'),
    (r'pC\b', 'pC'),
    (r'C\b', 'C'),
    # Energy variants
    (r'μJ\b', 'μJ'),
    (r'uJ\b', 'uJ'),
    (r'nJ\b', 'nJ'),
    (r'mJ\b', 'mJ'),
    (r'J\b', 'J'),
    # Time variants
    (r'μs\b', 'μs'),
    (r'us\b', 'us'),
    (r'ns\b', 'ns'),
    (r'ms\b', 'ms'),
    (r's\b', 's'),
    # Inductance variants
    (r'nH\b', 'nH'),
    (r'μH\b', 'μH'),
    (r'uH\b', 'uH'),
    (r'mH\b', 'mH'),
    (r'H\b', 'H'),
    # Mass
    (r'kg\b', 'kg'),
    (r'g\b', 'g'),
    # Length
    (r'mm\b', 'mm'),
    (r'cm\b', 'cm'),
    # Frequency variants
    (r'GHz\b', 'GHz'),
    (r'MHz\b', 'MHz'),
    (r'kHz\b', 'kHz'),
    (r'Hz\b', 'Hz'),
    # Power variants
    (r'MW\b', 'MW'),
    (r'kW\b', 'kW'),
    (r'W\b', 'W'),
]

# Numeric value patterns
NUMERIC_PATTERN = r'[+-]?\d+\.?\d*(?:[eE][+-]?\d+)?'
# Range pattern - supports:
# - "X to Y" (e.g., -40 to 150)
# - "X - Y" (e.g., 2 - 4, en dash)
# - "X – Y" (e.g., 2–4, em dash)
# - "X ~ Y" (e.g., -40 ~ 150)
# - "X ... Y" (e.g., -40 ... 150)
RANGE_PATTERN = r'([+-]?\d+\.?\d*(?:[eE][+-]?\d+)?)\s*(?:to|[-–—~…])\s*([+-]?\d+\.?\d*(?:[eE][+-]?\d+)?)'
PLUSMINUS_PATTERN = r'±\s*([+-]?\d+\.?\d*)'

# Column header patterns - must be EXACT matches for conservative detection
HEADER_PATTERNS = {
    'symbol': [r'^Symbol$', r'^Sym$', r'^Param$', r'^Parameter$'],
    'min': [r'^Min\.?$', r'^Minimum$'],
    'typ': [r'^Typ\.?$', r'^Typical$', r'^Nom\.?$', r'^Nominal$'],
    'max': [r'^Max\.?$', r'^Maximum$'],
    'unit': [r'^Unit$', r'^Units$'],
    'value': [r'^Value$', r'^Val$'],
    'condition': [r'^Condition$', r'^Conditions$', r'^Test Condition$', r'^Test Conditions$', r'^TC$', r'^Tj$'],
}

# Allowed units per field (Step 5.5)
ALLOWED_UNITS: Dict[str, Set[str]] = {
    'current_rating': {'A', 'mA', 'μA', 'uA', 'kA'},  # Step 5.9: added kA
    'voltage_rating': {'V', 'kV', 'mV'},  # Step 5.9: added mV
    'rds_on_25c': {'mΩ', 'Ω', 'kΩ'},
    'rds_on_150c': {'mΩ', 'Ω', 'kΩ'},
    'vgs_th': {'V', 'mV'},
    'ciss': {'pF', 'nF', 'μF', 'uF'},
    'coss': {'pF', 'nF', 'μF', 'uF'},
    'crss': {'pF', 'nF'},
    'qg': {'nC', 'μC', 'uC', 'pC'},
    'qgs': {'nC', 'μC', 'uC', 'pC'},
    'qgd': {'nC', 'μC', 'uC', 'pC'},
    'qrr': {'nC', 'μC', 'uC'},
    'eon': {'mJ', 'μJ', 'uJ', 'J'},
    'eoff': {'mJ', 'μJ', 'uJ', 'J'},
    'err': {'mJ', 'μJ', 'uJ', 'J'},
    'trr': {'ns', 'μs', 'us', 'ms'},
    'eoss': {'mJ', 'μJ', 'uJ', 'J'},
    'rth_jc': {'°C/W', 'K/W'},
    'rth_jh': {'°C/W', 'K/W'},
    'clearance_tt': {'mm'},
    'clearance_tb': {'mm'},
    'creepage_tt': {'mm'},
    'creepage_tb': {'mm'},
    'weight': {'g', 'kg'},
    'lstray': {'nH', 'μH', 'uH', 'nH'},
    'isol': {'kV', 'V'},
    'irrm': {'A', 'mA', 'μA'},
    'junction_temperature': {'°C'},
}

# High-risk fields
HIGH_RISK_FIELDS = {
    'current_rating', 'voltage_rating', 'vgs_th',
    'rds_on_25c', 'rds_on_150c',
    'clearance_tt', 'clearance_tb', 'creepage_tt', 'creepage_tb',
}


@dataclass
class ParsedValue:
    """Result of parsing a single value."""
    value: Optional[float] = None
    original_unit: str = ""
    confidence: str = "low"  # "high", "medium", "low"
    method: str = ""  # "header", "position", "fallback"


def normalize_unit(unit: str) -> str:
    """Normalize unit to standard form (preserve case for most units)."""
    if not unit:
        return ""
    unit = unit.strip()
    # Only normalize known ASCII aliases to unicode
    # Do NOT lowercase - 'A' != 'a' for unit comparison
    unit_map = {
        'ua': 'μA',
        'uA': 'μA',
        'uv': 'μV',
        'uV': 'μV',
        'uj': 'μJ',
        'uJ': 'μJ',
        'us': 'μs',
        'uS': 'μs',
        'uf': 'μF',
        'uF': 'μF',
        'uh': 'μH',
        'uH': 'μH',
        'uc': 'μC',
        'uC': 'μC',
    }
    return unit_map.get(unit, unit)


def is_range_text(text: str) -> bool:
    """Check if text is a range (e.g., '-40 to 150')."""
    if not text:
        return False
    text = text.strip()
    return bool(re.search(RANGE_PATTERN, text, re.IGNORECASE))


def is_slash_list_text(text: str) -> bool:
    """Check if text contains slash-separated numbers (e.g., '9/30/40')."""
    if not text:
        return False
    text = text.strip()
    # Must have at least 2 slashes with numeric content
    if text.count('/') < 1:
        return False
    parts = text.split('/')
    # At least 2 parts should be numeric
    numeric_count = 0
    for part in parts:
        part = part.strip()
        try:
            float(part)
            numeric_count += 1
        except ValueError:
            pass
    return numeric_count >= 2


def parse_range_values(text: str) -> Optional[Tuple[float, float]]:
    """Parse range text and return (min_value, max_value). Returns None if not a range."""
    if not text:
        return None
    text = text.strip()
    match = re.search(RANGE_PATTERN, text, re.IGNORECASE)
    if not match:
        return None
    try:
        min_val = float(match.group(1))
        max_val = float(match.group(2))
        return (min_val, max_val)
    except ValueError:
        return None


def parse_range_from_cells(row_cells: List[str], source_text: str = "") -> Optional[Dict[str, Any]]:
    """
    Parse range from split cells like ['2', '-', '4', 'V'] or single cells.
    Returns dict with min, max, unit, source, cells_used or None if not a range.
    
    Supports:
    - Split cells: ["2", "-", "4", "V"] / ["2", "–", "4", "V"] / ["-40", "to", "150", "°C"]
    - Single cell: "2 - 4 V" / "2–4 V" / "-40 to 150 °C"
    """
    # First try single-cell range check (existing logic)
    for i, cell in enumerate(row_cells):
        if is_range_text(cell):
            range_values = parse_range_values(cell)
            if range_values:
                # Try to find unit from adjacent cell
                unit = None
                for j in range(i + 1, min(i + 3, len(row_cells))):
                    candidate_unit = extract_unit(row_cells[j])
                    if candidate_unit:
                        unit = candidate_unit
                        break
                return {
                    "min": range_values[0],
                    "max": range_values[1],
                    "unit": unit,
                    "source": "single_cell",
                    "cells_used": [i],
                }
    
    # Try split-cell range detection
    range_separators = {'-', '–', '—', 'to', 'To', 'TO', '~'}
    
    for i, cell in enumerate(row_cells):
        cell_stripped = cell.strip()
        # Check if current cell is a separator
        if cell_stripped in range_separators:
            # Look for number before separator
            if i > 0:
                try:
                    min_val = float(row_cells[i - 1].strip())
                except ValueError:
                    continue
                # Look for number after separator
                if i + 1 < len(row_cells):
                    max_val_str = row_cells[i + 1].strip().rstrip('.,;:')
                    try:
                        max_val = float(max_val_str)
                    except ValueError:
                        continue
                    # Found valid range
                    # Try to find unit from next cell after max
                    unit = None
                    for j in range(i + 2, min(i + 4, len(row_cells))):
                        candidate_unit = extract_unit(row_cells[j])
                        if candidate_unit:
                            unit = candidate_unit
                            break
                    return {
                        "min": min_val,
                        "max": max_val,
                        "unit": unit,
                        "source": "split_cells",
                        "cells_used": [i - 1, i, i + 1],
                    }
    
    # Try to parse range from full source_text
    if source_text:
        range_values = parse_range_values(source_text)
        if range_values:
            # Try to find unit from source_text
            unit = extract_unit(source_text)
            return {
                "min": range_values[0],
                "max": range_values[1],
                "unit": unit,
                "source": "source_text",
                "cells_used": [],
            }
    
    return None


def is_figure_or_caption_row(source_text: str, row_cells: List[str]) -> bool:
    """
    Detect if a row is a figure/caption row (not a parameter row).
    Returns True if the row is a figure, caption, or chart label.
    
    Detects: Figure, Fig., 图, vs., versus, curve, chart, plot
    """
    if not source_text and not row_cells:
        return False
    
    # Combine text from source_text and row_cells
    all_text = source_text.lower()
    for cell in row_cells:
        all_text += " " + cell.lower()
    
    # Figure keywords
    figure_keywords = [
        "figure", "fig.", "fig ", "图", "curve", "chart", "plot",
        "vs. ", "vs ", "versus", "characteristic", "characteristics",
    ]
    
    for keyword in figure_keywords:
        if keyword in all_text:
            # Additional check: if it's just a figure reference in a table, still reject
            # But allow if the row has clear parameter structure
            if "parameter" in all_text or "symbol" in all_text or "typ" in all_text:
                # Might be a legitimate parameter row with figure reference
                # Be conservative: if it looks like a figure caption, reject
                if any(k in all_text for k in ["figure", "fig.", "fig ", "图", "vs.", "vs ", "versus"]):
                    return True
            else:
                return True
    
    return False


def parse_slash_values(text: str) -> Optional[List[float]]:
    """Parse slash-separated numbers and return list of values. Returns None if not slash-list."""
    if not text:
        return None
    text = text.strip()
    if not is_slash_list_text(text):
        return None
    parts = text.split('/')
    values = []
    for part in parts:
        part = part.strip()
        try:
            values.append(float(part))
        except ValueError:
            pass
    return values if values else None


def parse_number(text: str) -> Optional[float]:
    """
    Parse a number from text. Returns None for ranges, slash-lists, or plain numbers.
    
    Supports:
    - 39.6, 1.4, 84, 8.5, 5.3, 11.1
    - scientific notation (1.2e-3)
    - ±20 (extracts the number after ±)
    
    Does NOT treat as safe value:
    - -40 to 150 (range - use parse_range_values instead)
    - 9/30/40 (slash-list - use parse_slash_values instead)
    """
    if not text:
        return None
    
    text = text.strip()
    
    # Do NOT parse range as a single number (dangerous)
    if is_range_text(text):
        return None
    
    # Do NOT parse slash-list as a single number (dangerous)
    if is_slash_list_text(text):
        return None
    
    # Handle ± prefix
    plusminus_match = re.search(PLUSMINUS_PATTERN, text)
    if plusminus_match and '±' in text:
        try:
            return float(plusminus_match.group(1))
        except ValueError:
            pass
    
    # Handle scientific notation
    try:
        return float(text)
    except ValueError:
        pass
    
    # Try to extract first number from text
    match = re.search(NUMERIC_PATTERN, text)
    if match:
        try:
            return float(match.group(0))
        except ValueError:
            pass
    
    return None


def extract_unit(text: str) -> str:
    """
    Extract unit from text using longest-first UNIT_PATTERNS.
    
    Returns the normalized unit string if found, empty string otherwise.
    """
    if not text:
        return ""
    
    text = text.strip()
    
    for pattern, normalized_unit in UNIT_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return normalized_unit
    
    return ""


def extract_conditions(row_cells: List[str], source_text: str) -> Tuple[str, List[str]]:
    """
    Extract condition string from row cells or source text.
    
    Returns (condition_string, list_of_condition_values).
    """
    conditions = []
    condition_values = []  # e.g., ["VDS=800V", "ID=300A"]
    
    # Define condition patterns once at function level
    condition_patterns = [
        (r'T[ijc]\s*[=:]\s*([+-]?\d+)\s*°?C?', 'temperature'),
        (r'VDS\s*[=:]\s*([+-]?\d+\.?\d*)\s*V', 'vds'),
        (r'ID\s*[=:]\s*([+-]?\d+\.?\d*)\s*A', 'id'),
        (r'VGS\s*[=:]\s*([+-]?\d+\.?\d*)\s*V', 'vgs'),
        (r'f\s*[=:]\s*([+-]?\d+\.?\d*)\s*(Hz|kHz|MHz|GHz)', 'frequency'),
        (r'Terminal\s+to\s+Terminal', 't_t'),
        (r'Terminal\s+to\s+Baseplate', 't_b'),
        (r'\bT-T\b', 't_t'),
        (r'\bT-B\b', 't_b'),
    ]
    
    # Search in row cells
    for cell in row_cells:
        cell_clean = cell.strip()
        if not cell_clean:
            continue
        
        # Skip cells that look like numbers or units
        if parse_number(cell_clean) is not None:
            continue
        if extract_unit(cell_clean):
            continue
        
        for pattern, ptype in condition_patterns:
            match = re.search(pattern, cell_clean, re.IGNORECASE)
            if match:
                conditions.append(match.group(0))
                condition_values.append(match.group(0))
    
    # Search in source text
    for pattern, ptype in condition_patterns:
        match = re.search(pattern, source_text, re.IGNORECASE)
        if match and match.group(0) not in conditions:
            conditions.append(match.group(0))
            condition_values.append(match.group(0))
    
    return "; ".join(conditions), condition_values


def is_header_match(cell: str, header_patterns: List[str]) -> bool:
    """Check if a cell matches any of the header patterns."""
    cell_clean = cell.strip()
    for pattern in header_patterns:
        if re.match(pattern, cell_clean, re.IGNORECASE):
            return True
    return False


# Step 5.8: Condition cell and unit detection
CONDITION_PATTERNS = [
    r'VDS\s*[=:]',    # VDS=800V
    r'ID\s*[=:]',     # ID=300A
    r'VGS\s*[=:]',    # VGS=15V
    r'T[jic]\s*[=:]', # Tj=150°C, Tc=25°C
    r'f\s*[=:]',      # f=1MHz
    r'RG\s*[=:]',     # RG=10Ω
    r'dI/dt\s*[=:]',  # dI/dt=1000A/μs
    r'IF\s*[=:]',     # IF=300A
    r'Terminal\s+to\s+Terminal',  # Terminal to Terminal
    r'Terminal\s+to\s+Baseplate', # Terminal to Baseplate
    r'\bT-T\b',       # T-T
    r'\bT-B\b',       # T-B
]


def is_condition_cell(cell: str) -> bool:
    """
    Check if a cell is a condition cell (contains condition patterns).
    
    Examples of condition cells:
    - "VDS=800V"
    - "ID=300A"
    - "Tj=150°C"
    - "Terminal to Terminal"
    - "T-T"
    
    Returns True if the cell contains a condition pattern, False otherwise.
    """
    if not cell:
        return False
    cell_clean = cell.strip()
    for pattern in CONDITION_PATTERNS:
        if re.search(pattern, cell_clean, re.IGNORECASE):
            return True
    return False


def is_condition_unit_in_text(text: str, unit: str) -> bool:
    """
    Check if a unit appearing in text is part of a condition (not a main value unit).
    
    For example, in "VDS=800V", the "V" after "800" is part of the condition,
    not the main unit for the parameter.
    
    Returns True if the unit appears to be in a condition context.
    """
    if not text or not unit:
        return False
    
    # Build condition-like patterns that include the unit
    condition_unit_patterns = [
        rf'VDS\s*[=:].*{re.escape(unit)}',
        rf'ID\s*[=:].*{re.escape(unit)}',
        rf'VGS\s*[=:].*{re.escape(unit)}',
        rf'T[jic]\s*[=:].*{re.escape(unit)}',
        rf'f\s*[=:].*{re.escape(unit)}',
        rf'RG\s*[=:].*{re.escape(unit)}',
        rf'dI/dt\s*[=:].*{re.escape(unit)}',
        rf'IF\s*[=:].*{re.escape(unit)}',
    ]
    
    for pattern in condition_unit_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def extract_unit_for_param(
    field_id: str,
    row_cells: List[str],
    column_map: Dict[str, int],
    source_text: str,
    condition_values: List[str]
) -> Tuple[str, str, str]:
    """
    Extract unit for a parameter with conservative source tracking.
    
    Priority:
    1. unit_column - Explicit Unit column in the table
    2. value_cell - Unit embedded in the value cell itself (e.g., "300 A")
    3. adjacent_cell - Unit in a cell directly adjacent to value cell
    4. source_text_fallback - Unit found in full source text (lower confidence)
    5. not_found - No unit found
    
    Returns: (original_unit, unit_source, unit_warning)
    
    Rules:
    - Condition units (VDS=, ID=, VGS=, Tj=, etc.) are NOT used as original_unit
    - source_text_fallback reduces parse_quality to medium/low
    """
    original_unit = ""
    unit_source = "not_found"
    unit_warning = ""
    
    # Strategy 1: Check for explicit Unit column
    if 'unit' in column_map:
        unit_col_idx = column_map['unit']
        if unit_col_idx < len(row_cells):
            cell_unit = extract_unit(row_cells[unit_col_idx])
            if cell_unit:
                original_unit = cell_unit
                unit_source = "unit_column"
                return original_unit, unit_source, unit_warning
    
    # Strategy 2: Check value/min/typ/max cells for embedded units
    value_columns = []
    for col_type in ('value', 'typ', 'min', 'max'):
        if col_type in column_map:
            value_columns.append(column_map[col_type])
    
    for col_idx in value_columns:
        if col_idx < len(row_cells):
            cell = row_cells[col_idx]
            cell_unit = extract_unit(cell)
            if cell_unit:
                # Check if this unit is part of a condition
                if is_condition_unit_in_text(cell, cell_unit):
                    unit_warning = "unit_in_value_cell_but_is_condition"
                else:
                    original_unit = cell_unit
                    unit_source = "value_cell"
                    return original_unit, unit_source, unit_warning
    
    # Strategy 3: Check adjacent cells (immediately next to value column)
    for col_idx in value_columns:
        # Check cell to the right
        if col_idx + 1 < len(row_cells):
            adj_cell = row_cells[col_idx + 1]
            adj_unit = extract_unit(adj_cell)
            if adj_unit:
                # Adjacent cell is a standalone unit - verify it's not a condition
                if is_condition_cell(adj_cell):
                    unit_warning = "unit_in_adjacent_cell_but_is_condition"
                else:
                    original_unit = adj_unit
                    unit_source = "adjacent_cell"
                    return original_unit, unit_source, unit_warning
        
        # Check cell to the left
        if col_idx > 0:
            adj_cell = row_cells[col_idx - 1]
            adj_unit = extract_unit(adj_cell)
            if adj_unit:
                if is_condition_cell(adj_cell):
                    unit_warning = "unit_in_adjacent_cell_but_is_condition"
                else:
                    original_unit = adj_unit
                    unit_source = "adjacent_cell"
                    return original_unit, unit_source, unit_warning
    
    # Strategy 4: Source text fallback (lower confidence)
    # BUT skip condition-related units
    source_unit = extract_unit(source_text)
    if source_unit:
        # Verify it's not a condition unit
        if is_condition_unit_in_text(source_text, source_unit):
            unit_source = "source_text_fallback"
            unit_warning = "unit_from_source_text_but_is_condition_rejected"
            original_unit = ""  # Reject condition units
        else:
            original_unit = source_unit
            unit_source = "source_text_fallback"
            unit_warning = "unit_from_source_text_fallback"
    
    return original_unit, unit_source, unit_warning


def detect_column_structure_conservative(row_cells: List[str], nearby_headers: List[List[str]]) -> Dict[str, int]:
    """
    Detect column structure using CONSERVATIVE header matching.
    
    ONLY marks columns as min/typ/max if headers are EXACT matches.
    NO position-based fallback for min/typ/max when headers are absent.
    Without reliable headers, caller should mark values as partial/unsafe.
    
    Returns dict mapping column type to column index.
    """
    column_map: Dict[str, int] = {}
    
    # Only use header-based detection for min/typ/max
    for header_row in nearby_headers:
        for col_idx, cell in enumerate(header_row):
            if col_idx in column_map.values():
                continue
            
            for col_type, patterns in HEADER_PATTERNS.items():
                if is_header_match(cell, patterns):
                    column_map[col_type] = col_idx
                    break
    
    # If we found headers, use them strictly
    # If NO headers found, return empty column_map
    # DO NOT fall back to position-based min/typ/max detection
    # Without header, values should be marked as partial/unsafe
    
    return column_map


def has_condition_numeric(condition_values: List[str], test_value: float) -> bool:
    """Check if a test_value appears in any condition."""
    for cv in condition_values:
        # Extract numbers from condition
        numbers = re.findall(NUMERIC_PATTERN, cv)
        for num_str in numbers:
            try:
                if abs(float(num_str) - test_value) < 0.01:
                    return True
            except ValueError:
                pass
    return False


def unit_sanity_check(field_id: str, original_unit: str) -> Tuple[bool, str]:
    """
    Check if the unit is reasonable for the field.
    
    Returns (is_sane, reason).
    """
    if not original_unit:
        return True, ""  # No unit is OK (will be flagged elsewhere)
    
    allowed = ALLOWED_UNITS.get(field_id, set())
    if not allowed:
        return True, ""  # No restrictions for this field
    
    normalized = normalize_unit(original_unit)
    if normalized in allowed:
        return True, ""
    
    return False, f"unit_mismatch: expected {allowed}, got {original_unit}"


def reject_wrong_dimension_unit(
    field_id: str,
    extracted_unit: str,
    unit_source: str,
    unit_warning: str
) -> Tuple[str, str, str]:
    """
    Step 5.9: Reject wrong-dimension units before they pollute original_unit.
    
    If the extracted unit is not in ALLOWED_UNITS for the field, reject it.
    Returns (rejected_unit, new_unit_source, new_unit_warning).
    
    Rejected units are set to empty string, not to the wrong unit.
    """
    if not extracted_unit:
        return extracted_unit, unit_source, unit_warning
    
    allowed = ALLOWED_UNITS.get(field_id, set())
    if not allowed:
        # No restrictions defined, allow the unit
        return extracted_unit, unit_source, unit_warning
    
    normalized = normalize_unit(extracted_unit)
    if normalized in allowed:
        # Unit is acceptable
        return extracted_unit, unit_source, unit_warning
    
    # Unit is wrong dimension - REJECT it
    return "", f"rejected_wrong_dimension:{unit_source}", f"rejected_wrong_dimension:{extracted_unit}"


def parse_candidate_values(candidates: List[RawExtractedParam], extracted_pdfs: List[Dict[str, Any]] = None) -> List[RawExtractedParam]:
    """
    Parse values from active candidates with quality safeguards.
    
    Only processes candidates with candidate_status = 'active'.
    
    Step 5.5 changes:
    - Conservative column detection (only trust clear headers)
    - Unit sanity check per field
    - High-risk field special handling
    - Parse quality flags
    """
    # Only process active candidates
    active_candidates = [c for c in candidates if c.candidate_status == "active"]
    
    parsed_params: List[RawExtractedParam] = []
    
    for candidate in active_candidates:
        parse_status = "parsed"
        parse_quality = "medium"
        parse_warnings: List[str] = []
        unit_sanity_status = "ok"
        # Step 5.8: Track numeric tokens and value source columns
        numeric_tokens_detected: List[float] = []
        value_source_columns: List[str] = []
        
        # Skip if no row_cells available
        if not candidate.row_cells:
            candidate.review_reason = _add_review_reason(candidate.review_reason, "no_row_cells")
            parse_status = "failed"
            parse_quality = "low"
            candidate.min = None
            candidate.typ = None
            candidate.max = None
            candidate.value = None
            candidate.original_unit = ""
            candidate.normalized_unit = candidate.unit
            candidate.condition = ""
            candidate.condition_values = []
            parsed_params.append(candidate)
            continue
        
        row_cells = candidate.row_cells
        nearby_headers = candidate.nearby_header_rows
        source_text = candidate.source_text
        field_id = candidate.field_id
        
        # Step 5.9: Reject figure/caption rows early
        if is_figure_or_caption_row(source_text, row_cells):
            candidate.value = None
            candidate.min = None
            candidate.typ = None
            candidate.max = None
            candidate.original_unit = ""
            candidate.unit_source = "not_found"
            candidate.unit_warning = "figure_caption_rejected"
            candidate.parse_status = "failed"
            candidate.parse_quality = "low"
            review_reasons = ["figure_caption_not_parameter_row"]
            candidate.review_reason = "; ".join(review_reasons)
            parsed_params.append(candidate)
            continue
        
        # Detect column structure CONSERVATIVELY
        column_map = detect_column_structure_conservative(row_cells, nearby_headers)
        
        # Extract condition FIRST (before value parsing)
        condition_str, condition_values = extract_conditions(row_cells, source_text)
        
        # Initialize value tracking
        parsed_min = None
        parsed_typ = None
        parsed_max = None
        parsed_value = None
        original_unit = ""
        review_reasons: List[str] = []
        
        # Check if headers were found (conservative mode)
        headers_found = bool(column_map)
        
        # Parse min/typ/max/value from detected columns
        if 'typ' in column_map:
            typ_cell = row_cells[column_map['typ']]
            pv = parse_value_from_column(typ_cell, 'typ')
            if pv.value is not None:
                # Check if value is from condition
                if has_condition_numeric(condition_values, pv.value):
                    parse_warnings.append("typ_value_may_be_from_condition")
                else:
                    parsed_typ = pv.value
                    if pv.original_unit:
                        original_unit = pv.original_unit
                    # Step 5.8: Track tokens and source
                    numeric_tokens_detected.append(pv.value)
                    value_source_columns.append("typ_column")
        
        if 'min' in column_map:
            min_cell = row_cells[column_map['min']]
            pv = parse_value_from_column(min_cell, 'min')
            if pv.value is not None:
                if has_condition_numeric(condition_values, pv.value):
                    parse_warnings.append("min_value_may_be_from_condition")
                else:
                    parsed_min = pv.value
                    # Step 5.8: Track tokens and source
                    numeric_tokens_detected.append(pv.value)
                    value_source_columns.append("min_column")
        
        if 'max' in column_map:
            max_cell = row_cells[column_map['max']]
            pv = parse_value_from_column(max_cell, 'max')
            if pv.value is not None:
                if has_condition_numeric(condition_values, pv.value):
                    parse_warnings.append("max_value_may_be_from_condition")
                    review_reasons.append("value_column_suspect")
                else:
                    parsed_max = pv.value
                    # Step 5.8: Track tokens and source
                    numeric_tokens_detected.append(pv.value)
                    value_source_columns.append("max_column")
        
        # If no structured values found, try fallback but with warnings
        if parsed_typ is None and parsed_min is None and parsed_max is None:
            # Step 5.9: Try parse_range_from_cells first (handles split-cell ranges)
            range_result = parse_range_from_cells(row_cells, source_text)
            
            # Check for slash-list in row cells
            slash_cell = None
            for cell in row_cells:
                if is_slash_list_text(cell):
                    slash_cell = cell
                    break
            
            # Handle range result from parse_range_from_cells
            if range_result:
                range_min = range_result["min"]
                range_max = range_result["max"]
                range_unit = range_result.get("unit") or ""
                range_source = range_result.get("source", "range_cells")
                
                # vgs_th special handling: use range values directly
                if field_id == 'vgs_th':
                    parsed_min = range_min
                    parsed_max = range_max
                    parsed_value = None  # Clear any fallback value
                    parse_status = "parsed"
                    parse_quality = "high"
                    parse_warnings.append(f"range_parsed_from_{range_source}")
                    # Set unit from range if found
                    if range_unit:
                        original_unit = range_unit
                    # Track range values and mark source
                    numeric_tokens_detected.extend([range_min, range_max])
                    value_source_columns.append(f"range_from_{range_source}")
                # junction_temperature: use min/max directly (existing behavior)
                elif field_id == 'junction_temperature':
                    parsed_min = range_min
                    parsed_max = range_max
                    parse_status = "parsed"
                    parse_quality = "high"
                    parse_warnings.append(f"range_parsed_from_{range_source}")
                    numeric_tokens_detected.extend([range_min, range_max])
                    value_source_columns.append(f"range_from_{range_source}")
                else:
                    # Other fields: mark as partial but still report range
                    parsed_min = range_min
                    parsed_max = range_max
                    parse_status = "partial"
                    parse_quality = "low"
                    review_reasons.append("range_value_needs_review")
                    numeric_tokens_detected.extend([range_min, range_max])
                    value_source_columns.append(f"range_from_{range_source}")
            # Handle slash-list text specially (Step 5.8: don't take first number as safe value)
            elif slash_cell:
                slash_values = parse_slash_values(slash_cell)
                if slash_values:
                    parse_status = "partial"
                    parse_quality = "low"
                    review_reasons.append("slash_list_value_needs_review")
                    # Step 5.8: Track slash values in numeric_tokens_detected
                    numeric_tokens_detected.extend(slash_values)
                    value_source_columns.append("slash_list_detected")
                    parse_warnings.append(f"slash_list_values: {slash_values}")
                else:
                    parse_status = "failed"
                    review_reasons.append("slash_list_detected_but_not_parsed")
            # Regular fallback for plain numbers
            else:
                numbers_in_text = re.findall(NUMERIC_PATTERN, source_text)
                if numbers_in_text:
                    # Try to filter out condition numbers
                    valid_numbers = []
                    for num_str in numbers_in_text:
                        try:
                            num_val = float(num_str)
                            if not has_condition_numeric(condition_values, num_val):
                                valid_numbers.append(num_val)
                        except ValueError:
                            pass
                    
                    if valid_numbers:
                        parsed_value = valid_numbers[0]
                        parse_status = "partial"  # Fallback is partial quality
                        parse_quality = "low"
                        parse_warnings.append("value_from_text_fallback")
                        # Step 5.8: Track all valid numbers and source
                        numeric_tokens_detected.extend(valid_numbers)
                        value_source_columns.append("source_text_fallback")
                        if not headers_found:
                            review_reasons.append("no_reliable_header")
                    else:
                        parse_status = "failed"
                        review_reasons.append("no_value_parsed_non_condition")
                else:
                    parse_status = "failed"
                    review_reasons.append("no_value_parsed")
        
        # ========== Unit Extraction with Source Tracking (Step 5.8) ==========
        # Use conservative method: unit_column > value_cell > adjacent_cell > source_text_fallback
        unit_from_extraction, unit_source, unit_warning = extract_unit_for_param(
            field_id, row_cells, column_map, source_text, condition_values
        )
        # Step 5.9: Reject wrong-dimension units before they pollute original_unit
        rejected_unit, unit_source, unit_warning = reject_wrong_dimension_unit(
            field_id, unit_from_extraction, unit_source, unit_warning
        )
        if rejected_unit:
            original_unit = rejected_unit
        else:
            original_unit = ""
        # Track unit source for debugging (Step 5.8)
        candidate.unit_source = unit_source
        candidate.unit_warning = unit_warning
        if unit_warning:
            parse_warnings.append(unit_warning)
        
        # ========== Unit Sanity Check (Step 5.5) ==========
        if original_unit:
            is_sane, reason = unit_sanity_check(field_id, original_unit)
            if not is_sane:
                unit_sanity_status = "mismatch"
                review_reasons.append(reason)
                parse_quality = "low"
        
        # ========== Field-specific handling ==========
        
        # vgs_th: must have min/typ/max if possible
        if field_id == 'vgs_th':
            if parsed_min is None and parsed_typ is None and parsed_max is None:
                if parsed_value is not None:
                    review_reasons.append("partial_threshold_values")
                    parse_status = "partial"
                else:
                    review_reasons.append("vgs_th_missing_min_typ_max")
                    parse_status = "failed"
            # Check if max looks like a test condition value (e.g., VGS=15V)
            if parsed_max is not None and parsed_max < 20:  # VGS threshold is usually < 20V
                # This is suspicious - threshold max should be reasonable
                pass  # Let it through but with warning
        
        # rds_on: check condition mismatch
        if field_id in ('rds_on_25c', 'rds_on_150c'):
            if parse_condition_mismatch(field_id, condition_str):
                review_reasons.append("condition_mismatch")
                parse_quality = "low"
        
        # current_rating: high-risk field handling
        if field_id == 'current_rating':
            # Check if unit is A
            if original_unit and original_unit not in {'A', 'mA', 'μA', 'uA'}:
                unit_sanity_status = "mismatch"
                review_reasons.append("unit_mismatch: expected A, got " + original_unit)
                parse_quality = "low"
            
            # Check for test condition values
            if is_test_condition_value(condition_values):
                review_reasons.append("possible_test_condition_value")
                parse_quality = "low"
            
            # Check for ambiguous row (multiple unrelated units)
            units_in_row = set()
            for cell in row_cells:
                u = extract_unit(cell)
                if u:
                    units_in_row.add(u)
            if len(units_in_row) > 2:
                review_reasons.append("ambiguous_rating_row")
                parse_quality = "low"
            
            # Check for min > max (column order issue)
            if parsed_min is not None and parsed_max is not None:
                if parsed_min > parsed_max:
                    review_reasons.append("min_greater_than_max")
                    parse_quality = "low"
        
        # voltage_rating: high-risk field handling
        if field_id == 'voltage_rating':
            # Check if unit is V or kV
            if original_unit and original_unit not in {'V', 'kV'}:
                unit_sanity_status = "mismatch"
                review_reasons.append("unit_mismatch: expected V or kV, got " + original_unit)
                parse_quality = "low"
            
            # Don't confuse VGS, Visol, Vth with voltage_rating
            if condition_str and any(x in condition_str.lower() for x in ['vgs', 'visol', 'vth']):
                review_reasons.append("condition_contains_voltage_type")
                parse_quality = "low"
            
            # Check for min > max
            if parsed_min is not None and parsed_max is not None:
                if parsed_min > parsed_max:
                    review_reasons.append("min_greater_than_max")
                    parse_quality = "low"
        
        # clearance/creepage: must have condition
        if field_id in ('clearance_tt', 'clearance_tb', 'creepage_tt', 'creepage_tb'):
            if not condition_str:
                review_reasons.append("condition_unclear")
            else:
                # Check for T-T / T-B mismatch
                expected_type = 't_t' if 'tt' in field_id else 't_b'
                actual_type = None
                if 'terminal to terminal' in condition_str.lower() or 't-t' in condition_str.lower():
                    actual_type = 't_t'
                elif 'terminal to baseplate' in condition_str.lower() or 't-b' in condition_str.lower():
                    actual_type = 't_b'
                
                if actual_type and actual_type != expected_type:
                    review_reasons.append(f"condition_type_mismatch: expected {expected_type}, got {actual_type}")
                    parse_quality = "low"
        
        # For fields that should have units but don't
        if candidate.unit and not original_unit:
            review_reasons.append("unit_not_found")
        
        # Determine final parse_status
        if parse_status != "failed":
            if parsed_min is None and parsed_typ is None and parsed_max is None and parsed_value is None:
                parse_status = "failed"
            elif parse_quality == "low":
                parse_status = "unsafe"
            elif parse_warnings or unit_sanity_status == "mismatch":
                parse_status = "partial"
        
        # Update candidate with parsed values
        candidate.min = parsed_min
        candidate.typ = parsed_typ
        candidate.max = parsed_max
        candidate.value = parsed_value
        candidate.original_unit = original_unit
        candidate.normalized_unit = candidate.unit
        candidate.condition = condition_str
        # Store condition_values for debugging
        candidate.condition_values = condition_values
        # Step 5.8: Store numeric tokens and value source columns
        candidate.numeric_tokens_detected = numeric_tokens_detected
        candidate.value_source_columns = value_source_columns
        
        # Set unit conversion status
        if original_unit == candidate.unit or not original_unit:
            candidate.unit_conversion_status = UnitConversionStatus.NOT_NEEDED
        else:
            candidate.unit_conversion_status = UnitConversionStatus.NOT_SUPPORTED
        
        # Set review_reason
        if review_reasons:
            candidate.review_reason = _add_review_reason(candidate.review_reason, "; ".join(review_reasons))
        
        # Write parse quality fields (Step 5.5)
        candidate.parse_status = parse_status
        candidate.parse_quality = parse_quality
        candidate.parse_warning = "; ".join(parse_warnings) if parse_warnings else ""
        candidate.unit_sanity_status = unit_sanity_status
        
        parsed_params.append(candidate)
    
    return parsed_params


def parse_value_from_column(cell_text: str, column_type: str) -> ParsedValue:
    """
    Parse a value from a single cell based on column type.
    
    Returns ParsedValue with value, unit, confidence, and method.
    """
    if not cell_text or not cell_text.strip():
        return ParsedValue()
    
    cell = cell_text.strip()
    
    # Parse number
    number = parse_number(cell)
    if number is None:
        return ParsedValue()
    
    # Extract unit from cell
    unit = extract_unit(cell)
    
    # Determine confidence based on column type
    confidence = "low"
    if column_type in ('min', 'typ', 'max', 'value'):
        if unit:
            confidence = "high"
        else:
            confidence = "medium"
    
    return ParsedValue(
        value=number,
        original_unit=unit,
        confidence=confidence,
        method="header" if column_type else "position"
    )


def parse_condition_mismatch(field_id: str, condition: str) -> bool:
    """
    Check if there's a condition mismatch for rds_on fields.
    
    For rds_on_25c: condition should mention 25°C
    For rds_on_150c: condition should mention 150°C
    """
    if field_id == 'rds_on_25c':
        if re.search(r'150\s*°?C', condition, re.IGNORECASE):
            return True
    elif field_id == 'rds_on_150c':
        # Check if condition shows 25°C but NOT 150°C
        if re.search(r'25\s*°?C', condition, re.IGNORECASE) and not re.search(r'150', condition):
            return True
    
    return False


def is_test_condition_value(condition_values: List[str]) -> bool:
    """
    Check if any condition value looks like a test condition.
    
    High-risk for current_rating and voltage_rating.
    """
    test_patterns = [
        r'VDS\s*[=:]\s*\d+',  # e.g., VDS=800V
        r'ID\s*[=:]\s*\d+',    # e.g., ID=300A
        r'VGS\s*[=:]\s*\d+',  # e.g., VGS=15V
    ]
    
    for cv in condition_values:
        for pattern in test_patterns:
            if re.search(pattern, cv, re.IGNORECASE):
                return True
    
    return False


def _add_review_reason(existing: str, new_reason: str) -> str:
    """Add a new review reason to existing review_reason."""
    if existing:
        return f"{existing}; {new_reason}"
    return new_reason


def params_to_debug_json(parsed_params: List[RawExtractedParam], candidates: List[RawExtractedParam]) -> Dict[str, Any]:
    """
    Convert parsed params to debug JSON structure with Step 5.5 fields.
    """
    # Group by document
    by_doc: Dict[str, List[RawExtractedParam]] = {}
    for p in parsed_params:
        doc_id = p.document_id
        if doc_id not in by_doc:
            by_doc[doc_id] = []
        by_doc[doc_id].append(p)
    
    # Count stats
    active_count = sum(1 for c in candidates if c.candidate_status == "active")
    parsed_value_count = sum(1 for p in parsed_params if p.typ is not None or p.min is not None or p.max is not None or p.value is not None)
    failed_parse_count = sum(1 for p in parsed_params if p.typ is None and p.min is None and p.max is None and p.value is None)
    
    # Parse quality counts
    parse_status_counts = {"parsed": 0, "failed": 0, "partial": 0, "unsafe": 0}
    parse_quality_counts = {"high": 0, "medium": 0, "low": 0}
    unit_mismatch_count = 0
    
    for p in parsed_params:
        # Determine parse_status from review_reason and values
        if p.typ is None and p.min is None and p.max is None and p.value is None:
            parse_status_counts["failed"] += 1
        elif "unit_mismatch" in (p.review_reason or ""):
            parse_status_counts["unsafe"] += 1
        elif any(x in (p.review_reason or "") for x in ["ambiguous", "suspect", "condition_mismatch", "possible_test_condition"]):
            parse_status_counts["partial"] += 1
        else:
            parse_status_counts["parsed"] += 1
        
        # Determine parse_quality
        if "unit_mismatch" in (p.review_reason or ""):
            parse_quality_counts["low"] += 1
        elif any(x in (p.review_reason or "") for x in ["condition_mismatch", "possible_test_condition", "min_greater_than_max"]):
            parse_quality_counts["low"] += 1
        elif "from_text_fallback" in (p.review_reason or "") or "partial" in (p.review_reason or ""):
            parse_quality_counts["medium"] += 1
        else:
            parse_quality_counts["high"] += 1
        
        # Count unit mismatches
        if "unit_mismatch" in (p.review_reason or ""):
            unit_mismatch_count += 1
    
    pdfs_out = []
    for doc_id, params in by_doc.items():
        params_list = []
        parsed_fields = set()
        failed_fields = set()
        
        for p in params:
            has_value = p.typ is not None or p.min is not None or p.max is not None or p.value is not None
            if has_value:
                parsed_fields.add(p.field_id)
            else:
                failed_fields.add(p.field_id)
            
            # Build param dict with Step 5.5 fields
            param_dict = p.to_dict()
            
            # Add Step 5.5 specific fields
            # Determine parse_status
            if p.typ is None and p.min is None and p.max is None and p.value is None:
                param_dict["parse_status"] = "failed"
            elif "unit_mismatch" in (p.review_reason or ""):
                param_dict["parse_status"] = "unsafe"
            elif any(x in (p.review_reason or "") for x in ["ambiguous", "suspect", "condition_mismatch"]):
                param_dict["parse_status"] = "partial"
            else:
                param_dict["parse_status"] = "parsed"
            
            # Determine parse_quality
            if "unit_mismatch" in (p.review_reason or ""):
                param_dict["parse_quality"] = "low"
            elif any(x in (p.review_reason or "") for x in ["condition_mismatch", "possible_test_condition", "min_greater_than_max"]):
                param_dict["parse_quality"] = "low"
            elif "from_text_fallback" in (p.review_reason or "") or "partial" in (p.review_reason or ""):
                param_dict["parse_quality"] = "medium"
            else:
                param_dict["parse_quality"] = "high"
            
            # Determine parse_warning
            parse_warnings = []
            if "from_text_fallback" in (p.review_reason or ""):
                parse_warnings.append("value_from_text_fallback")
            if "_value_may_be_from_condition" in (p.review_reason or ""):
                parse_warnings.append("value_may_be_from_condition")
            if "ambiguous" in (p.review_reason or ""):
                parse_warnings.append("ambiguous_row")
            param_dict["parse_warning"] = "; ".join(parse_warnings) if parse_warnings else ""
            
            # Unit sanity status
            if "unit_mismatch" in (p.review_reason or ""):
                param_dict["unit_sanity_status"] = "mismatch"
            elif not p.original_unit and p.unit:
                param_dict["unit_sanity_status"] = "missing"
            else:
                param_dict["unit_sanity_status"] = "ok"
            
            # Value source columns (for debugging)
            if hasattr(p, 'condition_values'):
                param_dict["condition_values"] = p.condition_values
            
            params_list.append(param_dict)
        
        pdfs_out.append({
            "document_id": doc_id,
            "file_name": params[0].file_name if params else "",
            "pdf_stem": params[0].pdf_stem if params else "",
            "raw_param_count": len(params),
            "parsed_fields": sorted(parsed_fields),
            "failed_fields": sorted(failed_fields),
            "params": params_list,
        })
    
    return {
        "raw_param_count": len(parsed_params),
        "active_candidate_count": active_count,
        "parsed_value_count": parsed_value_count,
        "failed_parse_count": failed_parse_count,
        "parse_status_counts": parse_status_counts,
        "parse_quality_counts": parse_quality_counts,
        "unit_mismatch_count": unit_mismatch_count,
        "pdfs": pdfs_out,
    }


def generate_value_parse_audit(parsed_params: List[RawExtractedParam], candidates: List[RawExtractedParam], target_field_ids: List[str] = None) -> str:
    """
    Generate value parsing audit markdown report with Step 5.5 sections.
    """
    # Group by field_id
    by_field: Dict[str, List[RawExtractedParam]] = {}
    for p in parsed_params:
        if p.field_id not in by_field:
            by_field[p.field_id] = []
        by_field[p.field_id].append(p)
    
    # Stats
    active_count = sum(1 for c in candidates if c.candidate_status == "active")
    parsed_value_count = sum(1 for p in parsed_params if p.typ is not None or p.min is not None or p.max is not None or p.value is not None)
    failed_parse_count = sum(1 for p in parsed_params if p.typ is None and p.min is None and p.max is None and p.value is None)
    
    # Parse quality counts
    parse_status_counts = {"parsed": 0, "failed": 0, "partial": 0, "unsafe": 0}
    parse_quality_counts = {"high": 0, "medium": 0, "low": 0}
    unit_mismatch_count = 0
    ambiguous_count = 0
    
    for p in parsed_params:
        if p.typ is None and p.min is None and p.max is None and p.value is None:
            parse_status_counts["failed"] += 1
        elif "unit_mismatch" in (p.review_reason or ""):
            parse_status_counts["unsafe"] += 1
            unit_mismatch_count += 1
        elif any(x in (p.review_reason or "") for x in ["ambiguous", "suspect", "condition_mismatch", "possible_test_condition"]):
            parse_status_counts["partial"] += 1
            if "ambiguous" in (p.review_reason or ""):
                ambiguous_count += 1
        else:
            parse_status_counts["parsed"] += 1
        
        if "unit_mismatch" in (p.review_reason or ""):
            parse_quality_counts["low"] += 1
        elif any(x in (p.review_reason or "") for x in ["condition_mismatch", "possible_test_condition", "min_greater_than_max"]):
            parse_quality_counts["low"] += 1
        elif "from_text_fallback" in (p.review_reason or "") or "partial" in (p.review_reason or ""):
            parse_quality_counts["medium"] += 1
        else:
            parse_quality_counts["high"] += 1
    
    # Fields with/without values
    fields_with_values = set()
    fields_without_values = set()
    for field_id, params in by_field.items():
        has_value = any(p.typ is not None or p.min is not None or p.max is not None or p.value is not None for p in params)
        if has_value:
            fields_with_values.add(field_id)
        else:
            fields_without_values.add(field_id)
    
    # Unit mismatch fields
    unit_mismatch_fields = set()
    for p in parsed_params:
        if "unit_mismatch" in (p.review_reason or ""):
            unit_mismatch_fields.add(p.field_id)
    
    lines = []
    lines.append("# Value Parse Audit (Step 5.9)")
    lines.append("")
    
    # Section 0: Field ID Validation (Step 5.5)
    lines.append("## 0. Field ID Validation")
    lines.append("")
    all_param_field_ids = set(by_field.keys())
    
    # Real validation against target_field_ids
    if target_field_ids is None:
        # No target provided - cannot validate
        target_set = all_param_field_ids
        invalid_field_ids = set()
        missing_from_parsed = set()
        validation_status = "UNKNOWN (no target_field_ids provided)"
    else:
        target_set = set(target_field_ids)
        invalid_field_ids = all_param_field_ids - target_set  # IDs in params but not in target
        missing_from_parsed = target_set - all_param_field_ids  # IDs in target but not in params
        if invalid_field_ids:
            validation_status = "FAIL"
        elif missing_from_parsed:
            validation_status = "WARN (some target fields not in parsed)"
        else:
            validation_status = "PASS"
    
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total unique field_ids | {len(all_param_field_ids)} |")
    lines.append(f"| Invalid field_ids | {len(invalid_field_ids)} |")
    if invalid_field_ids:
        lines.append(f"| Invalid IDs list | {', '.join(sorted(invalid_field_ids))} |")
    lines.append(f"| Missing from parsed | {len(missing_from_parsed)} |")
    if missing_from_parsed:
        lines.append(f"| Missing IDs list | {', '.join(sorted(missing_from_parsed))} |")
    lines.append(f"| Validation status | **{validation_status}** |")
    lines.append("")
    
    # Section 1: Overview
    lines.append("## 1. Overview")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Active Candidates | {active_count} |")
    lines.append(f"| Parsed Value Count | {parsed_value_count} |")
    lines.append(f"| Failed Parse Count | {failed_parse_count} |")
    lines.append(f"| Fields with Values | {len(fields_with_values)} |")
    lines.append(f"| Fields without Values | {len(fields_without_values)} |")
    lines.append("")
    
    # Section 1.5: Parse Quality Breakdown (Step 5.5)
    lines.append("## 1.5. Parse Quality Breakdown")
    lines.append("")
    lines.append(f"| Metric | Count |")
    lines.append(f"|--------|-------|")
    lines.append(f"| parse_status=parsed | {parse_status_counts['parsed']} |")
    lines.append(f"| parse_status=partial | {parse_status_counts['partial']} |")
    lines.append(f"| parse_status=unsafe | {parse_status_counts['unsafe']} |")
    lines.append(f"| parse_status=failed | {parse_status_counts['failed']} |")
    lines.append(f"| parse_quality=high | {parse_quality_counts['high']} |")
    lines.append(f"| parse_quality=medium | {parse_quality_counts['medium']} |")
    lines.append(f"| parse_quality=low | {parse_quality_counts['low']} |")
    lines.append(f"| unit_mismatch | {unit_mismatch_count} |")
    lines.append("")
    
    # Section 1.6: Unit Mismatch Summary (Step 5.5)
    lines.append("## 1.6. Unit Mismatch Summary")
    lines.append("")
    if unit_mismatch_fields:
        lines.append(f"| Field ID | Issue |")
        lines.append(f"|----------|-------|")
        for fid in sorted(unit_mismatch_fields):
            params = by_field.get(fid, [])
            mismatches = [p for p in params if "unit_mismatch" in (p.review_reason or "")]
            lines.append(f"| {fid} | {len(mismatches)} unit mismatches |")
        lines.append("")
    else:
        lines.append("*No unit mismatches found.*")
        lines.append("")
    
    # Section 1.7: Ambiguous Numeric Columns (Step 5.5)
    lines.append("## 1.7. Ambiguous Numeric Columns")
    lines.append("")
    ambiguous_params = [p for p in parsed_params if "ambiguous" in (p.review_reason or "")]
    if ambiguous_params:
        lines.append(f"| Field ID | Page | Table | Row | Issue |")
        lines.append(f"|----------|------|-------|-----|-------|")
        for p in ambiguous_params[:10]:
            lines.append(f"| {p.field_id} | {p.source_page} | {p.table_index} | {p.row_index} | {p.review_reason} |")
        lines.append("")
    else:
        lines.append("*No ambiguous numeric columns found.*")
        lines.append("")
    
    # Section 2: Parse Success by Field
    lines.append("## 2. Parse Success by Field")
    lines.append("")
    lines.append(f"| Field ID | Cand | Parsed | Failed | parse_status | Units Found | Issues |")
    lines.append(f"|----------|------|--------|--------|--------------|-------------|--------|")
    
    sorted_fields = sorted(by_field.keys(), key=lambda x: len(by_field[x]), reverse=True)
    for field_id in sorted_fields:
        params = by_field[field_id]
        parsed = sum(1 for p in params if p.typ is not None or p.min is not None or p.max is not None or p.value is not None)
        failed = len(params) - parsed
        
        # Determine parse_status for this field
        field_parse_statuses = set()
        for p in params:
            if p.typ is None and p.min is None and p.max is None and p.value is None:
                field_parse_statuses.add("failed")
            elif "unit_mismatch" in (p.review_reason or ""):
                field_parse_statuses.add("unsafe")
            elif any(x in (p.review_reason or "") for x in ["ambiguous", "suspect", "condition_mismatch"]):
                field_parse_statuses.add("partial")
            else:
                field_parse_statuses.add("parsed")
        
        status_str = ",".join(sorted(field_parse_statuses))
        
        # Collect units found
        units = set(p.original_unit for p in params if p.original_unit)
        units_str = ", ".join(sorted(units)) if units else "-"
        
        # Collect issues
        issues = set()
        for p in params:
            if p.review_reason:
                for r in p.review_reason.split("; "):
                    if r and r not in ("unit_not_found", "no_value_parsed"):
                        issues.add(r)
        issues_str = ", ".join(sorted(issues))[:60] if issues else "-"
        
        lines.append(f"| {field_id} | {len(params)} | {parsed} | {failed} | {status_str} | {units_str} | {issues_str} |")
    lines.append("")
    
    # Section 3: High-risk Rating Fields (Step 5.5)
    lines.append("## 3. High-risk Rating Fields")
    lines.append("")
    
    high_risk = ['current_rating', 'voltage_rating']
    
    for field_id in high_risk:
        if field_id not in by_field:
            lines.append(f"### {field_id}")
            lines.append("")
            lines.append("*No candidates found.*")
            lines.append("")
            continue
        
        params = by_field[field_id]
        lines.append(f"### {field_id}")
        lines.append("")
        lines.append(f"Total: {len(params)} candidates")
        
        # Check specific issues
        unit_mismatches = [p for p in params if "unit_mismatch" in (p.review_reason or "")]
        test_cond = [p for p in params if "possible_test_condition_value" in (p.review_reason or "")]
        ambiguous = [p for p in params if "ambiguous_rating_row" in (p.review_reason or "")]
        min_gt_max = [p for p in params if "min_greater_than_max" in (p.review_reason or "")]
        
        if unit_mismatches:
            lines.append(f"**Unit mismatches**: {len(unit_mismatches)}")
        if test_cond:
            lines.append(f"**Possible test condition values**: {len(test_cond)}")
        if ambiguous:
            lines.append(f"**Ambiguous rows**: {len(ambiguous)}")
        if min_gt_max:
            lines.append(f"**Min > Max (column order issue)**: {len(min_gt_max)}")
        
        lines.append("")
        
        # Show examples
        for p in params[:3]:
            values_str = []
            if p.min is not None:
                values_str.append(f"min={p.min}")
            if p.typ is not None:
                values_str.append(f"typ={p.typ}")
            if p.max is not None:
                values_str.append(f"max={p.max}")
            if p.value is not None:
                values_str.append(f"value={p.value}")
            
            values_display = ", ".join(values_str) if values_str else "NO VALUE"
            unit_display = f"{p.original_unit} / normalized: {p.normalized_unit}" if p.original_unit else f"normalized: {p.normalized_unit}"
            condition_display = p.condition[:80] if p.condition else "(no condition)"
            review_display = p.review_reason[:100] if p.review_reason else "-"
            
            lines.append(f"**Page {p.source_page}, Table {p.table_index}, Row {p.row_index}**")
            lines.append(f"- Values: {values_display}")
            lines.append(f"- Unit: {unit_display}")
            lines.append(f"- Condition: {condition_display}")
            lines.append(f"- Review: {review_display}")
            lines.append("")
    
    # Section 4: VGS(th) Check (Step 5.5, updated Step 5.9)
    lines.append("## 4. VGS(th) Check")
    lines.append("")
    
    if 'vgs_th' in by_field:
        vgs_params = by_field['vgs_th']
        lines.append(f"Total: {len(vgs_params)} candidates")
        lines.append("")
        lines.append(f"| Page | Table | min | max | value | Unit | unit_source | parse_status | parse_quality | Review |")
        lines.append(f"|------|-------|-----|-----|-------|------|-------------|--------------|-------|")
        
        for p in vgs_params:
            unit_src = getattr(p, 'unit_source', '') or '-'
            num_tokens = getattr(p, 'numeric_tokens_detected', []) or []
            val_src_cols = getattr(p, 'value_source_columns', []) or []
            min_val = p.min if p.min is not None else '-'
            max_val = p.max if p.max is not None else '-'
            val_val = p.value if p.value is not None else '-'
            lines.append(f"| {p.source_page} | {p.row_index} | {min_val} | {max_val} | {val_val} | {p.original_unit} | {unit_src} | {getattr(p, 'parse_status', '-')} | {getattr(p, 'parse_quality', '-')} | {(p.review_reason or '-')[:60]} |")
        
        lines.append("")
        lines.append("**Details with source_text and range info (Step 5.9):**")
        lines.append("")
        
        for p in vgs_params:
            source_text = p.source_text[:200] + "..." if len(p.source_text) > 200 else p.source_text
            num_tokens = getattr(p, 'numeric_tokens_detected', []) or []
            val_src_cols = getattr(p, 'value_source_columns', []) or []
            lines.append(f"**Page {p.source_page}, Row {p.row_index}**: \"{source_text}\"")
            lines.append(f"- min={p.min}, max={p.max}, value={p.value}")
            lines.append(f"- unit={p.original_unit}, unit_source={getattr(p, 'unit_source', '-')}, unit_warning={getattr(p, 'unit_warning', '-')}")
            lines.append(f"- numeric_tokens_detected={num_tokens}")
            lines.append(f"- value_source_columns={val_src_cols}")
            lines.append(f"- condition={p.condition}")
            lines.append(f"- review_reason={p.review_reason}")
            lines.append("")
    else:
        lines.append("*No vgs_th candidates found.*")
        lines.append("")
    
    # Section 5: Example Values by Field
    lines.append("## 5. Example Values by Field")
    lines.append("")
    
    for field_id in sorted_fields[:10]:
        params = by_field[field_id]
        lines.append(f"### {field_id}")
        lines.append("")
        
        for p in params[:2]:
            values_str = []
            if p.min is not None:
                values_str.append(f"min={p.min}")
            if p.typ is not None:
                values_str.append(f"typ={p.typ}")
            if p.max is not None:
                values_str.append(f"max={p.max}")
            if p.value is not None:
                values_str.append(f"value={p.value}")
            
            values_display = ", ".join(values_str) if values_str else "NO VALUE"
            source_text = p.source_text[:120] + "..." if len(p.source_text) > 120 else p.source_text
            
            lines.append(f"**Page {p.source_page}, Row {p.row_index}**: {values_display}")
            lines.append(f"- Unit: {p.original_unit or '-'} | Condition: {p.condition[:50] if p.condition else '-'}")
            lines.append(f"- Source: \"{source_text}\"")
            if p.review_reason:
                lines.append(f"- Review: {p.review_reason}")
            lines.append("")
    
    # ========== Step 5.8: New Audit Sections ==========
    
    # Section 6: Unit Source Summary (Step 5.8)
    lines.append("## 6. Unit Source Summary")
    lines.append("")
    unit_source_counts = {"unit_column": 0, "value_cell": 0, "adjacent_cell": 0, "source_text_fallback": 0, "not_found": 0, "rejected_wrong_dimension": 0}
    wrong_dim_rejected_by_field = {}
    for p in parsed_params:
        src = getattr(p, 'unit_source', '') or 'not_found'
        if 'rejected_wrong_dimension' in src:
            unit_source_counts['rejected_wrong_dimension'] += 1
            fid = p.field_id
            if fid not in wrong_dim_rejected_by_field:
                wrong_dim_rejected_by_field[fid] = 0
            wrong_dim_rejected_by_field[fid] += 1
        elif src in unit_source_counts:
            unit_source_counts[src] += 1
        else:
            unit_source_counts['not_found'] += 1
    lines.append(f"| Unit Source | Count |")
    lines.append(f"|-------------|-------|")
    for src, count in unit_source_counts.items():
        lines.append(f"| {src} | {count} |")
    lines.append("")
    if wrong_dim_rejected_by_field:
        lines.append(f"**Wrong dimension rejected by field**: {dict(wrong_dim_rejected_by_field)}")
        lines.append("")
    
    # Section 7: Condition Unit Exclusion Summary (Step 5.8)
    lines.append("## 7. Condition Unit Exclusion Summary")
    lines.append("")
    condition_rejected_count = 0
    condition_rejected_fields = set()
    for p in parsed_params:
        uw = getattr(p, 'unit_warning', '') or ''
        if 'condition' in uw.lower() or 'condition_rejected' in uw.lower():
            condition_rejected_count += 1
            condition_rejected_fields.add(p.field_id)
    lines.append(f"| Metric | Count |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Params with condition units rejected | {condition_rejected_count} |")
    lines.append(f"| Fields affected | {len(condition_rejected_fields)} |")
    if condition_rejected_fields:
        lines.append(f"| Field list | {', '.join(sorted(condition_rejected_fields))} |")
    lines.append("")
    
    # Section 8: Range Parsing Summary (Step 5.8)
    lines.append("## 8. Range Parsing Summary")
    lines.append("")
    range_params = [p for p in parsed_params if hasattr(p, 'value_source_columns') and 'range_text' in (p.value_source_columns or [])]
    if range_params:
        lines.append(f"| Field ID | Page | min | max | Unit | Condition | Review |")
        lines.append(f"|----------|------|-----|-----|------|----------|--------|")
        for p in range_params[:10]:
            lines.append(f"| {p.field_id} | {p.source_page} | {p.min} | {p.max} | {p.original_unit} | {p.condition[:30] if p.condition else '-'} | {p.review_reason[:50] if p.review_reason else '-'} |")
        lines.append("")
    else:
        lines.append("*No range values detected.*")
        lines.append("")
    
    # Section 9: Slash-list Summary (Step 5.8)
    lines.append("## 9. Slash-list Summary")
    lines.append("")
    slash_params = [p for p in parsed_params if hasattr(p, 'value_source_columns') and 'slash_list_detected' in (p.value_source_columns or [])]
    if slash_params:
        lines.append(f"| Field ID | Page | numeric_tokens | Source | Review |")
        lines.append(f"|----------|------|---------------|--------|--------|")
        for p in slash_params[:10]:
            tokens = getattr(p, 'numeric_tokens_detected', []) or []
            tokens_str = ', '.join(str(t) for t in tokens[:5])
            lines.append(f"| {p.field_id} | {p.source_page} | [{tokens_str}] | slash_list | {p.review_reason[:50] if p.review_reason else '-'} |")
        lines.append("")
    else:
        lines.append("*No slash-list values detected.*")
        lines.append("")
    
    # Section 10: Clearance/Creepage T-T/T-B Check (Step 5.8)
    lines.append("## 10. Clearance/Creepage T-T/T-B Check")
    lines.append("")
    clearance_creepage_fields = ['clearance_tt', 'clearance_tb', 'creepage_tt', 'creepage_tb']
    tt_tb_data = {}
    for fid in clearance_creepage_fields:
        if fid in by_field:
            tt_tb_data[fid] = by_field[fid]
    if tt_tb_data:
        lines.append(f"| Field ID | Count | Accepted TT | Accepted TB | Mismatch | Condition Unclear |")
        lines.append(f"|----------|-------|-------------|-------------|----------|-------------------|")
        for fid, params in tt_tb_data.items():
            accepted_tt = 0
            accepted_tb = 0
            mismatch = 0
            unclear = 0
            for p in params:
                rr = (p.review_reason or '').lower()
                if 'condition_type_mismatch' in rr:
                    mismatch += 1
                elif 'condition_unclear' in rr:
                    unclear += 1
                elif 'tt' in fid:
                    accepted_tt += 1
                elif 'tb' in fid:
                    accepted_tb += 1
            total = len(params)
            lines.append(f"| {fid} | {total} | {accepted_tt} | {accepted_tb} | {mismatch} | {unclear} |")
        lines.append("")
        lines.append("**Detail:**")
        lines.append("")
        for fid, params in tt_tb_data.items():
            lines.append(f"### {fid}")
            lines.append("")
            for p in params:
                source_text = p.source_text[:150] + "..." if len(p.source_text) > 150 else p.source_text
                condition = p.condition[:80] if p.condition else '(no condition)'
                rr = p.review_reason[:100] if p.review_reason else '-'
                lines.append(f"- Page {p.source_page}, Table {p.table_index}, Row {p.row_index}")
                lines.append(f"  - Value: {p.value} {p.original_unit}")
                lines.append(f"  - Condition: {condition}")
                lines.append(f"  - Review: {rr}")
                lines.append(f"  - Source: \"{source_text}\"")
                lines.append("")
    else:
        lines.append("*No clearance/creepage candidates found.*")
        lines.append("")
    
    # ========== Step 5.9: New Audit Sections ==========
    
    # Section 11: Figure/Caption Rejection Summary (Step 5.9)
    lines.append("## 11. Figure/Caption Rejection Summary (Step 5.9)")
    lines.append("")
    figure_rejected_params = []
    for p in parsed_params:
        rr = (p.review_reason or '').lower()
        if 'figure_caption_not_parameter_row' in rr:
            figure_rejected_params.append(p)
    
    if figure_rejected_params:
        lines.append(f"**Total rejected: {len(figure_rejected_params)}**")
        lines.append("")
        lines.append(f"| Field ID | Page | Row | source_text |")
        lines.append(f"|----------|------|-----|-------------|")
        for p in figure_rejected_params:
            src = p.source_text[:100] + "..." if len(p.source_text) > 100 else p.source_text
            lines.append(f"| {p.field_id} | {p.source_page} | {p.row_index} | {src} |")
        lines.append("")
    else:
        lines.append("*No figure/caption rows rejected.*")
        lines.append("")
    
    # Section 12: Wrong Dimension Unit Rejection Summary (Step 5.9)
    lines.append("## 12. Wrong Dimension Unit Rejection Summary (Step 5.9)")
    lines.append("")
    wrong_dim_rejected = []
    for p in parsed_params:
        uw = getattr(p, 'unit_warning', '') or ''
        if 'rejected_wrong_dimension' in uw:
            wrong_dim_rejected.append(p)
    
    lines.append(f"| Metric | Count |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total wrong dimension rejected | {len(wrong_dim_rejected)} |")
    lines.append("")
    
    # Group by field
    by_field_wrong_dim = {}
    for p in wrong_dim_rejected:
        fid = p.field_id
        if fid not in by_field_wrong_dim:
            by_field_wrong_dim[fid] = []
        by_field_wrong_dim[fid].append(p)
    
    if by_field_wrong_dim:
        lines.append(f"| Field ID | Count | Rejected Units |")
        lines.append(f"|----------|-------|----------------|")
        for fid, params in sorted(by_field_wrong_dim.items()):
            rejected_units = set()
            for p in params:
                uw = getattr(p, 'unit_warning', '') or ''
                # Extract the rejected unit from warning like "rejected_wrong_dimension:mΩ"
                if ':' in uw:
                    rejected_units.add(uw.split(':')[1])
            lines.append(f"| {fid} | {len(params)} | {', '.join(sorted(rejected_units))} |")
        lines.append("")
        
        lines.append("**Detail:**")
        lines.append("")
        for fid, params in sorted(by_field_wrong_dim.items()):
            lines.append(f"### {fid}")
            lines.append("")
            for p in params:
                uw = getattr(p, 'unit_warning', '') or '-'
                src = p.source_text[:120] + "..." if len(p.source_text) > 120 else p.source_text
                lines.append(f"- Page {p.source_page}, Row {p.row_index}: unit_warning={uw}")
                lines.append(f"  - source_text: \"{src}\"")
                lines.append(f"  - value={p.value}, unit_source={getattr(p, 'unit_source', '-')}")
                lines.append("")
    else:
        lines.append("*No wrong dimension units rejected.*")
        lines.append("")
    
    return "\n".join(lines)
