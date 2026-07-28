"""
materialize_parameter_inventory.py — Generate Parameter Inventory from EnrichedPayload.

Phase 5: Extract all parameter rows from PDF, not just predefined target fields.

Rules:
1. RowType.PARAMETER → goes to inventory
2. RowType.UNKNOWN but looks like parameter → goes to needs_review
3. table title, column header, metadata_kv, empty → NOT included
4. Duplicate parameters kept (not deleted)
5. Slot assignment based on table schema (Values vs Min/Typ/Max)
6. No LLM involvement
7. No field name hardcoding
"""

import re
from typing import Any

from .models import EnrichedPayload, EnrichedPage, EnrichedTable, EnrichedRow, RowType
from .parameter_inventory_models import (
    ParameterRecord,
    InventoryReport,
    MappingStatus,
    ExtractionStatus,
)


# ─────────────────────────────────────────────────────────────────────────────
# Unit Inference
# ─────────────────────────────────────────────────────────────────────────────

# Known unit mappings for common parameter symbols
# These are inferred when the unit is not extracted from the PDF
_UNIT_INFERENCE_RULES: list[tuple[re.Pattern, str]] = [
    # Capacitance (F, farads) → nF
    (re.compile(r"\bC(?:ies|iss|oss|rss|res|o|gs|gd)?\b", re.IGNORECASE), "nF"),
    # Energy (J, joules) → mJ
    (re.compile(r"\bE(?:on|off|rec|c|sw)?\b", re.IGNORECASE), "mJ"),
    # Charge (Q, coulombs) → nC
    (re.compile(r"\bQ(?:gd|gs|g|oss|id)?\b", re.IGNORECASE), "nC"),
    # Time (s, seconds) → ns
    (re.compile(r"\b(?:t|t_)d(?:_?on|_?off)?\b|\btr\b|\btf\b|\btd\b|\btrr\b|\btt\b|\bps\b", re.IGNORECASE), "ns"),
    # Inductance (H, henrys) → nH or μH
    (re.compile(r"\bL(?:s|stray)?\b", re.IGNORECASE), "nH"),
    # Resistance (Ω, ohms) → mΩ
    (re.compile(r"\bR(?:DS|_th|_jc|_ch)?\b", re.IGNORECASE), "mΩ"),
    # Voltage (V) → V (already correct in most cases)
    (re.compile(r"\bV(?:GS|DS|th|br|dd|cc|gs|ds)?\b", re.IGNORECASE), "V"),
    # Current (A) → A
    (re.compile(r"\bI(?:D|fs|DSS|ds|GSS|gs|s|f)?\b", re.IGNORECASE), "A"),
    # Power (W) → W
    (re.compile(r"\bP(?:D|d|loss)?\b", re.IGNORECASE), "W"),
    # Frequency (Hz) → kHz or MHz
    (re.compile(r"\bf(?:sw|osc|res|_r)?\b", re.IGNORECASE), "kHz"),
    # Temperature (°C) → °C
    (re.compile(r"\bT(?:j|th|c|a|stg)?\b", re.IGNORECASE), "°C"),
    # Speed/ Slew rate → V/ns
    (re.compile(r"\b(?:dv|di)_?dt\b", re.IGNORECASE), "V/ns"),
]


def _infer_unit(symbol: str | None) -> str | None:
    """
    Infer the unit based on the parameter symbol.

    This is used when the unit is not extracted from the PDF.
    """
    if not symbol:
        return None

    for pattern, unit in _UNIT_INFERENCE_RULES:
        if pattern.search(symbol):
            return unit

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _is_parameter_like_row(enriched_row: EnrichedRow, table_headers: list[str]) -> bool:
    """
    Check if an UNKNOWN row looks like a parameter.

    Criteria:
    - Row has numeric value (can be parsed as float)
    - Table has Values or Min/Typ/Max/Unit schema
    - Not a title, header, metadata, or comment
    """
    cells = enriched_row.raw_cells
    if len(cells) < 2:
        return False

    # Check if table has parameter table schema
    header_str = " ".join(table_headers).lower()
    has_values_schema = "values" in header_str or "min" in header_str or "typ" in header_str or "max" in header_str
    has_unit = "unit" in header_str

    if not (has_values_schema or has_unit):
        return False

    # Check if row has at least one numeric value
    for cell in cells[1:]:  # Skip first cell (usually symbol)
        if cell and cell.strip() and _is_numeric_cell(cell):
            return True

    return False


def _is_numeric_cell(cell: str) -> bool:
    """Check if a cell contains a numeric value."""
    if not cell or not cell.strip():
        return False

    # Remove common units and special characters
    cleaned = re.sub(r"[Ωµμ·•\sA-Z°%\/]", "", cell.strip())

    # Handle negative numbers and scientific notation
    cleaned = cleaned.replace("−", "-").replace("–", "-")

    # Check if it's a number
    try:
        float(cleaned)
        return True
    except ValueError:
        return False


def _parse_numeric(cell: str) -> float | None:
    """Parse a numeric value from a cell string."""
    if not cell or not cell.strip():
        return None

    # Remove common units and special characters
    cleaned = re.sub(r"[Ωµμ·•\sA-Z°%\/]", "", cell.strip())

    # Handle negative numbers and scientific notation
    cleaned = cleaned.replace("−", "-").replace("–", "-")

    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_value(cell: str) -> str | float | None:
    """
    Parse a value from a cell string, supporting both numeric and range values.

    Returns:
        - float for numeric values
        - str for range values (e.g., "-10/+22", "-40 to +175")
        - None for empty or unparseable values
    """
    if not cell or not cell.strip():
        return None

    # First try to parse as numeric
    numeric_val = _parse_numeric(cell)
    if numeric_val is not None:
        return numeric_val

    # Check if it's a range pattern
    cell_stripped = cell.strip()

    # Range patterns: "X to Y", "X/Y", "X~Y", "X-Y" (but not negative numbers)
    # We need to be careful not to match negative numbers as ranges
    range_patterns = [
        r"[+-]?\d+(\.\d+)?\s+to\s+[+-]?\d+(\.\d+)?",  # "-40 to +175"
        r"[+-]?\d+(\.\d+)?\s*/\s*[+-]?\d+(\.\d+)?",  # "-10/+22"
        r"[+-]?\d+(\.\d+)?\s*~\s*[+-]?\d+(\.\d+)?",  # "100~200"
    ]

    for pattern in range_patterns:
        if re.search(pattern, cell_stripped):
            # Extract the range and clean it minimally
            # Remove units but preserve the range structure
            cleaned = re.sub(r"[Ωµμ·•\sA-Z°%]", " ", cell_stripped)
            cleaned = " ".join(cleaned.split())  # Normalize whitespace
            return cleaned

    return None


def _detect_table_schema(table_headers: list[str], rows: list[EnrichedRow]) -> str:
    """
    Detect the schema type of a table.

    Returns:
        "values": Symbol | Parameter | Values | Unit (4 columns)
        "min_typ_max": Symbol | Parameter | Min | Typ | Max | Unit (6+ columns)
        "unknown": Cannot determine
    """
    header_str = " ".join(table_headers).lower()

    # Check for Values schema
    if "values" in header_str and "min" not in header_str and "typ" not in header_str:
        return "values"

    # Check for Min/Typ/Max schema
    if "min" in header_str or "typ" in header_str or "max" in header_str:
        return "min_typ_max"

    # Fallback: check column count
    if len(table_headers) >= 5:
        return "min_typ_max"
    elif len(table_headers) >= 4:
        return "values"

    return "unknown"


def _get_column_roles(headers: list[str]) -> dict[str, int]:
    """
    Map header names to column indices.

    Returns dict like:
    {
        "symbol": 0,
        "parameter": 1,
        "min": 2,
        "typ": 3,
        "max": 4,
        "unit": 5,
        "values": 2,
    }
    """
    roles = {}
    header_lower = [h.lower() for h in headers]

    # Find symbol column (usually first)
    for i, h in enumerate(header_lower):
        if "symbol" in h or "parameter" in h or "characteristics" in h:
            if "symbol" not in roles:
                roles["symbol"] = i

    # Find parameter column
    for i, h in enumerate(header_lower):
        if "parameter" in h or "characteristics" in h:
            roles["parameter"] = i

    # Find min column
    for i, h in enumerate(header_lower):
        if h.strip() == "min" or "min." in h or "minimum" in h:
            roles["min"] = i
            break

    # Find typ column
    for i, h in enumerate(header_lower):
        if h.strip() == "typ" or "typ." in h or "typical" in h:
            roles["typ"] = i
            break

    # Find max column
    for i, h in enumerate(header_lower):
        if h.strip() == "max" or "max." in h or "maximum" in h:
            roles["max"] = i
            break

    # Find values column
    for i, h in enumerate(header_lower):
        if h.strip() == "values" or "value" in h:
            roles["values"] = i
            break

    # Find unit column
    for i, h in enumerate(header_lower):
        if "unit" in h:
            roles["unit"] = i
            break

    return roles


def _extract_slots_from_row(
    enriched_row: EnrichedRow,
    table_headers: list[str],
    schema_type: str,
) -> tuple[float | None, float | None, float | None, float | None, str | None]:
    """
    Extract value slots from a row based on table schema.

    Returns: (value, min, typ, max, unit)

    Values table: value = Values column
    Min/Typ/Max table: min/typ/max from respective columns
    """
    cells = enriched_row.raw_cells
    if len(cells) < 2:
        return None, None, None, None, None

    roles = _get_column_roles(table_headers)

    # Extract unit
    unit = None
    if "unit" in roles and roles["unit"] < len(cells):
        unit = cells[roles["unit"]].strip() if cells[roles["unit"]] else None

    if schema_type == "values":
        # Values table: Symbol | Parameter | Values | Unit
        values_idx = roles.get("values", 2)
        if values_idx < len(cells):
            value = _parse_value(cells[values_idx])
            return value, None, None, None, unit
        return None, None, None, None, unit

    elif schema_type == "min_typ_max":
        # Min/Typ/Max table: Symbol | Parameter | Min | Typ | Max | Unit
        min_val = None
        typ_val = None
        max_val = None

        # Handle incomplete headers: if header is shorter than expected for min_typ_max,
        # use default column positions based on cell count
        num_cells = len(cells)

        # If "min" is not found but we have enough cells, use default position 2
        if "min" not in roles and num_cells >= 3:
            roles["min"] = 2
        if "typ" not in roles and num_cells >= 4:
            roles["typ"] = 3
        if "max" not in roles and num_cells >= 5:
            roles["max"] = 4
        # If "unit" is not found but we have enough cells, use default position 5
        if "unit" not in roles and num_cells >= 6:
            roles["unit"] = 5
        # Update unit if we found the unit column (either from header or default)
        if "unit" in roles and roles["unit"] < len(cells):
            if cells[roles["unit"]]:
                unit = cells[roles["unit"]].strip()

        if "min" in roles and roles["min"] < len(cells):
            min_val = _parse_numeric(cells[roles["min"]])

        if "typ" in roles and roles["typ"] < len(cells):
            typ_val = _parse_numeric(cells[roles["typ"]])

        if "max" in roles and roles["max"] < len(cells):
            max_val = _parse_numeric(cells[roles["max"]])

        return None, min_val, typ_val, max_val, unit

    return None, None, None, None, unit


def _extract_symbol_and_name(cells: list[str], headers: list[str]) -> tuple[str | None, str | None]:
    """
    Extract symbol and parameter name from row cells.

    First cell is typically the symbol (e.g., "VDS", "ID").
    Remaining cells before the first numeric value form the parameter name.
    """
    if not cells:
        return None, None

    symbol = cells[0].strip() if cells[0] else None

    # Parameter name is typically the second cell (after symbol)
    # or the concatenation of non-numeric cells
    if len(cells) > 1:
        # Skip symbol (first cell) and unit (usually last)
        name_parts = []
        for cell in cells[1:]:
            cell = cell.strip()
            if cell and not _is_numeric_cell(cell):
                name_parts.append(cell)
        parameter_name = " ".join(name_parts) if name_parts else None
    else:
        parameter_name = None

    return symbol, parameter_name


def _extract_embedded_value_from_name(parameter_name: str) -> tuple[str | None, str | None, str | None]:
    """
    Extract embedded value and unit from parameter name if present.

    Some PDFs embed the value and unit in the parameter name cell.
    E.g., "Gate-Source Voltage (dynamic) -10/+22 V" -> 
          name="Gate-Source Voltage (dynamic)", value="-10/+22", unit="V"

    Returns: (cleaned_name, extracted_value, extracted_unit)
    """
    if not parameter_name:
        return None, None, None

    # Pattern: parameter_name + value_pattern + unit
    # Value patterns: "-10/+22", "-40 to +175", "100~200", etc.
    # Unit patterns: "V", "A", "°C", "mΩ", "nF", etc.

    # Try to find a value pattern followed by a unit
    # Common value patterns in parameter names
    value_patterns = [
        r"([+-]?\d+(\.\d+)?\s*/\s*[+-]?\d+(\.\d+)?)",  # "-10/+22", "100/200"
        r"([+-]?\d+(\.\d+)?\s+to\s+[+-]?\d+(\.\d+)?)",  # "-40 to +175"
        r"([+-]?\d+(\.\d+)?\s*[~－-]\s*[+-]?\d+(\.\d+)?)",  # "100~200", "100-200"
    ]

    # Unit patterns (typically at the end of the value)
    unit_patterns = [
        r"V\b",  # Voltage
        r"A\b",  # Amperes
        r"°C\b",  # Temperature
        r"mΩ\b",  # Milliohm
        r"MΩ\b",  # Megaohm
        r"Ω\b",  # Ohm
        r"nF\b",  # Nanofarad
        r"µF\b",  # Microfarad
        r"pF\b",  # Picofarad
        r"mJ\b",  # Millijoule
        r"µJ\b",  # Microjoule
        r"nC\b",  # Nanocoulomb
        r"µC\b",  # Microcoulomb
        r"mH\b",  # Millihenry
        r"µH\b",  # Microhenry
        r"ns\b",  # Nanosecond
        r"µs\b",  # Microsecond
        r"ms\b",  # Millisecond
        r"W\b",  # Watt
        r"kW\b",  # Kilowatt
        r"MW\b",  # Megawatt
        r"Hz\b",  # Hertz
        r"kHz\b",  # Kilohertz
        r"MHz\b",  # Megahertz
        r"GHz\b",  # Gigahertz
        r"N\b",  # Newton
        r"Nm\b",  # Newton-meter
        r"mNm\b",  # Millinewton-meter
        r"Pa\b",  # Pascal
        r"kPa\b",  # Kilopascal
        r"MPa\b",  # Megapascal
        r"mm\b",  # Millimeter
        r"cm\b",  # Centimeter
        r"m\b",  # Meter
        r"µm\b",  # Micrometer
        r"%",  # Percentage
    ]

    name = parameter_name
    extracted_value = None
    extracted_unit = None

    # Try to find a value pattern
    for pattern in value_patterns:
        match = re.search(pattern, parameter_name)
        if match:
            extracted_value = match.group(1).strip()
            # Remove the value from the name
            name = name[:match.start()].strip() + name[match.end():].strip()
            name = re.sub(r"\s+", " ", name).strip()  # Normalize whitespace
            break

    # Try to find a unit (after the value, or in the remaining name)
    if extracted_value:
        # Look for unit after the value
        remaining = parameter_name[match.end():] if match else parameter_name
        for unit_pattern in unit_patterns:
            unit_match = re.search(unit_pattern, remaining)
            if unit_match:
                extracted_unit = unit_match.group(0)
                # Remove the unit from the remaining text (not from name, since we already removed the value part)
                break
    else:
        # No value found, look for unit in the entire name
        for unit_pattern in unit_patterns:
            unit_match = re.search(unit_pattern, parameter_name)
            if unit_match:
                extracted_unit = unit_match.group(0)
                # Don't remove unit from name, just return it
                break

    return name if name else None, extracted_value, extracted_unit


def _build_source_text(cells: list[str], resolved_condition: str | None = None) -> str:
    """
    Build a text representation of the row.

    If resolved_condition is provided, include it.
    """
    parts = [c.strip() for c in cells if c and c.strip()]
    text = " | ".join(parts)

    if resolved_condition:
        text += f" @ {resolved_condition}"

    return text


# ─────────────────────────────────────────────────────────────────────────────
# Main Inventory Generation
# ─────────────────────────────────────────────────────────────────────────────

def materialize_parameter_inventory(enriched_payload: EnrichedPayload) -> tuple[list[ParameterRecord], InventoryReport]:
    """
    Generate Parameter Inventory from EnrichedPayload.

    This function does NOT use LLM - it's purely deterministic extraction
    from the enriched data.

    Returns:
        Tuple of (list of ParameterRecord, InventoryReport)
    """
    records: list[ParameterRecord] = []
    report = InventoryReport()

    # Track pages and tables
    pages_seen = set()
    tables_seen = set()

    for page in enriched_payload.pages:
        pages_seen.add(page.page_number)

        for table in page.tables:
            tables_seen.add((page.page_number, table.table_index))

            # Track the most recent column_header for each row
            # Tables can have multiple column_header rows (e.g., Values schema followed by Min/Typ/Max schema)
            current_header: list[str] = []
            schema_type: str = "unknown"

            for row in table.rows:
                # Update current_header when we encounter a column_header row
                if row.row_type == RowType.COLUMN_HEADER:
                    current_header = row.raw_cells
                    schema_type = _detect_table_schema(current_header, table.rows)
                    if schema_type == "values":
                        report.values_table_count += 1
                    elif schema_type == "min_typ_max":
                        report.min_typ_max_table_count += 1
                    continue

                # Skip non-parameter rows
                if row.row_type not in (RowType.PARAMETER, RowType.UNKNOWN):
                    continue

                # Use the most recent header for this row
                table_headers = current_header

                # Check if UNKNOWN row looks like a parameter
                is_parameter_like = False
                if row.row_type == RowType.UNKNOWN:
                    if _is_parameter_like_row(row, table_headers):
                        is_parameter_like = True
                        report.unknown_parameter_like += 1
                    else:
                        report.unknown_rows_found += 1
                        continue

                if row.row_type == RowType.PARAMETER:
                    report.parameter_rows_found += 1

                # Extract slot values using the most recent header and detected schema
                value, min_val, typ_val, max_val, unit = _extract_slots_from_row(
                    row, table_headers, schema_type
                )

                # Check for missing value slots
                if value is None and min_val is None and typ_val is None and max_val is None:
                    report.missing_value_slots += 1

                # Extract symbol and name
                symbol, parameter_name = _extract_symbol_and_name(row.raw_cells, table_headers)

                # Extract embedded value from parameter name if value is still None
                # Some PDFs embed the value in the parameter name cell
                if value is None and parameter_name:
                    cleaned_name, extracted_value, extracted_unit = _extract_embedded_value_from_name(parameter_name)
                    if extracted_value:
                        value = extracted_value
                        parameter_name = cleaned_name  # Update the parameter name
                        if unit is None and extracted_unit:
                            unit = extracted_unit

                # Infer unit if not extracted from PDF
                if unit is None:
                    inferred_unit = _infer_unit(symbol)
                    if inferred_unit:
                        unit = inferred_unit

                # Build source text
                source_text = _build_source_text(row.raw_cells, row.resolved_condition)
                source_text_reconstructed = False

                # Check for missing source text
                if not source_text or source_text.strip() == "":
                    source_text = " | ".join([c.strip() for c in row.raw_cells if c and c.strip()])
                    source_text_reconstructed = True
                    report.missing_source_text += 1

                if source_text_reconstructed:
                    report.reconstructed_source_text += 1

                # Determine if row has complete structure (for mapping_status decision)
                # Complete = has min+max+unit AND condition (from resolved_condition or Test Conditions column with 7+ cells)
                has_cond_from_cell = len(row.raw_cells) > 6 and any(c and c.strip() for c in row.raw_cells[6:])
                is_complete_structure = bool(min_val is not None and max_val is not None and unit and
                                            (row.resolved_condition or has_cond_from_cell))

                # Create parameter record
                record = ParameterRecord(
                    record_id=f"inv_{row.page_number}_{row.table_index}_{row.row_index}",
                    file_name=enriched_payload.file_name,
                    page_number=row.page_number,
                    table_index=row.table_index,
                    row_index=row.row_index,
                    row_id=row.row_id,
                    section_title=row.section_title,
                    table_title=row.table_title,
                    symbol=symbol,
                    parameter_name=parameter_name,
                    value=value,
                    min=min_val,
                    typ=typ_val,
                    max=max_val,
                    unit=unit,
                    raw_condition=row.raw_condition,
                    resolved_condition=row.resolved_condition,
                    source_schema_type=schema_type,
                    source_headers=table_headers,
                    source_cells=row.raw_cells,
                    source_text=source_text,
                    source_text_reconstructed=source_text_reconstructed,
                    extraction_status=ExtractionStatus.DIRECT,
                    quality_flags=list(row.quality_flags) if row.quality_flags else [],
                    # Complete unmapped parameters -> UNMAPPED (not NEEDS_REVIEW)
                    mapping_status=MappingStatus.UNMAPPED if (is_parameter_like and is_complete_structure) else
                                (MappingStatus.NEEDS_REVIEW if is_parameter_like else MappingStatus.UNMAPPED),
                )

                records.append(record)

    # Update report
    report.pages_covered = len(pages_seen)
    report.tables_covered = len(tables_seen)

    # Count mapping statuses
    for record in records:
        if record.mapping_status == MappingStatus.MAPPED:
            report.mapped_count += 1
        elif record.mapping_status == MappingStatus.UNMAPPED:
            report.unmapped_count += 1
        elif record.mapping_status == MappingStatus.NEEDS_REVIEW:
            report.needs_review_count += 1
        elif record.mapping_status == MappingStatus.DUPLICATE:
            report.duplicate_count += 1

    return records, report
