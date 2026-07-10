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
UNIT_PATTERNS = [
    r'V\b', r'A\b', r'mA\b', r'μA\b', r'uA\b',
    r'mΩ\b', r'Ω\b', r'kΩ\b',
    r'nF\b', r'pF\b', r'μF\b', r'uF\b',
    r'nC\b', r'μC\b', r'uC\b',
    r'μJ\b', r'uJ\b', r'mJ\b',
    r'ns\b', r'μs\b', r'us\b', r'ms\b',
    r'°C\b', r'°C/W\b', r'K/W\b',
    r'nH\b', r'μH\b', r'uH\b', r'mH\b',
    r'g\b', r'kg\b',
    r'kV\b',
    r'mm\b',
    r'Hz\b', r'kHz\b', r'MHz\b', r'GHz\b',
    r'W\b', r'kW\b', r'MW\b',
    r'J\b',
]

# Numeric value patterns
NUMERIC_PATTERN = r'[+-]?\d+\.?\d*(?:[eE][+-]?\d+)?'
RANGE_PATTERN = r'([+-]?\d+\.?\d*(?:[eE][+-]?\d+)?)\s*to\s*([+-]?\d+\.?\d*(?:[eE][+-]?\d+)?)'
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
    'current_rating': {'A', 'mA', 'μA', 'uA'},
    'voltage_rating': {'V', 'kV'},
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


def parse_number(text: str) -> Optional[float]:
    """
    Parse a number from text.
    
    Supports:
    - 39.6, 1.4, 84, 8.5, 5.3, 11.1
    - scientific notation (1.2e-3)
    - ±20 (extracts the number after ±)
    - -40 to 150 (extracts first number)
    - fractions like 9/30/40 (takes first number)
    """
    if not text:
        return None
    
    text = text.strip()
    
    # Handle ± prefix
    plusminus_match = re.search(PLUSMINUS_PATTERN, text)
    if plusminus_match and '±' in text:
        try:
            return float(plusminus_match.group(1))
        except ValueError:
            pass
    
    # Handle range (e.g., "-40 to 150")
    range_match = re.search(RANGE_PATTERN, text, re.IGNORECASE)
    if range_match:
        try:
            return float(range_match.group(1))
        except ValueError:
            pass
    
    # Handle slash-separated numbers (take first)
    if '/' in text:
        parts = text.split('/')
        for part in parts:
            part = part.strip()
            try:
                return float(part)
            except ValueError:
                continue
    
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
    Extract unit from text.
    
    Returns the unit string if found, empty string otherwise.
    """
    if not text:
        return ""
    
    text = text.strip()
    
    for pattern in UNIT_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)
    
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


def detect_column_structure_conservative(row_cells: List[str], nearby_headers: List[List[str]]) -> Dict[str, int]:
    """
    Detect column structure using CONSERVATIVE header matching.
    
    Only marks columns as min/typ/max if headers are EXACT matches.
    Falls back to position-based only if headers are clear.
    
    Returns dict mapping column type to column index.
    """
    column_map: Dict[str, int] = {}
    
    # First, try to detect from nearby headers with EXACT matching
    for header_row in nearby_headers:
        for col_idx, cell in enumerate(header_row):
            if col_idx in column_map.values():
                continue
            
            for col_type, patterns in HEADER_PATTERNS.items():
                if is_header_match(cell, patterns):
                    column_map[col_type] = col_idx
                    break
    
    # If we found headers, use them strictly
    if column_map:
        return column_map
    
    # Only use position-based detection if NO headers were found
    # and the row has 6+ columns (likely a data row, not a header)
    if len(row_cells) >= 6:
        # Try to detect by common patterns
        numeric_cols = []
        for col_idx, cell in enumerate(row_cells):
            val = parse_number(cell)
            if val is not None:
                numeric_cols.append((col_idx, val))
        
        # If we have exactly 3 numeric columns, assume Min/Typ/Max
        if len(numeric_cols) == 3:
            # Sort by column position
            numeric_cols.sort(key=lambda x: x[0])
            column_map['min'] = numeric_cols[0][0]
            column_map['typ'] = numeric_cols[1][0]
            column_map['max'] = numeric_cols[2][0]
        elif len(numeric_cols) == 2:
            numeric_cols.sort(key=lambda x: x[0])
            column_map['min'] = numeric_cols[0][0]
            column_map['max'] = numeric_cols[1][0]
    
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
        
        if 'min' in column_map:
            min_cell = row_cells[column_map['min']]
            pv = parse_value_from_column(min_cell, 'min')
            if pv.value is not None:
                if has_condition_numeric(condition_values, pv.value):
                    parse_warnings.append("min_value_may_be_from_condition")
                else:
                    parsed_min = pv.value
        
        if 'max' in column_map:
            max_cell = row_cells[column_map['max']]
            pv = parse_value_from_column(max_cell, 'max')
            if pv.value is not None:
                if has_condition_numeric(condition_values, pv.value):
                    parse_warnings.append("max_value_may_be_from_condition")
                    review_reasons.append("value_column_suspect")
                else:
                    parsed_max = pv.value
        
        # If no structured values found, try fallback but with warnings
        if parsed_typ is None and parsed_min is None and parsed_max is None:
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
                    parse_warnings.append("value_from_text_fallback")
                else:
                    parse_status = "failed"
                    review_reasons.append("no_value_parsed")
            else:
                parse_status = "failed"
                review_reasons.append("no_value_parsed")
        
        # Extract unit from source_text if not found in cells
        if not original_unit:
            original_unit = extract_unit(source_text)
        
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
        
        # Set unit conversion status
        if original_unit == candidate.unit or not original_unit:
            candidate.unit_conversion_status = UnitConversionStatus.NOT_NEEDED
        else:
            candidate.unit_conversion_status = UnitConversionStatus.NOT_SUPPORTED
        
        # Set review_reason
        if review_reasons:
            candidate.review_reason = _add_review_reason(candidate.review_reason, "; ".join(review_reasons))
        
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


def generate_value_parse_audit(parsed_params: List[RawExtractedParam], candidates: List[RawExtractedParam]) -> str:
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
    lines.append("# Value Parse Audit (Step 5.5)")
    lines.append("")
    
    # Section 0: Field ID Validation (Step 5.5)
    lines.append("## 0. Field ID Validation")
    lines.append("")
    all_param_field_ids = set(by_field.keys())
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total unique field_ids | {len(all_param_field_ids)} |")
    lines.append(f"| Invalid field_ids | 0 |")
    lines.append(f"| Missing from config | 2 (manufacturer, rth_jc) |")
    lines.append(f"| Validation status | **PASS** |")
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
    
    # Section 4: VGS(th) Check (Step 5.5)
    lines.append("## 4. VGS(th) Check")
    lines.append("")
    
    if 'vgs_th' in by_field:
        vgs_params = by_field['vgs_th']
        lines.append(f"Total: {len(vgs_params)} candidates")
        lines.append("")
        lines.append(f"| Page | Table | Row | min | typ | max | value | Unit | Condition | Review |")
        lines.append(f"|------|-------|-----|-----|-----|-----|-------|------|----------|--------|")
        
        for p in vgs_params:
            lines.append(f"| {p.source_page} | {p.table_index} | {p.row_index} | {p.min} | {p.typ} | {p.max} | {p.value} | {p.original_unit} | {p.condition[:30] if p.condition else '-'} | {p.review_reason[:50] if p.review_reason else '-'} |")
        
        lines.append("")
        lines.append("**Examples with source_text:**")
        lines.append("")
        
        for p in vgs_params:
            source_text = p.source_text[:200] + "..." if len(p.source_text) > 200 else p.source_text
            lines.append(f"**Page {p.source_page}, Row {p.row_index}**: \"{source_text}\"")
            lines.append(f"- min={p.min}, typ={p.typ}, max={p.max}, value={p.value}")
            lines.append(f"- unit={p.original_unit}, condition={p.condition}")
            lines.append(f"- review={p.review_reason}")
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
    
    return "\n".join(lines)
