"""
heading_parser.py — Parse temperature conditions from section/table heading text.

Handles patterns like:
- "at TC=25°C unless otherwise specified"
- "(at TJ=25℃ unless otherwise specified)"
- "TC=25°C"
- "TJ=25°C"
- "Tj = 25 °C"
- "TJ=25 C"
- negative temperatures: TJ=-55°C
- decimal temperatures: TC=25.5°C

All results normalized to:
- key: "TC" or "TJ" (uppercase)
- value: e.g., "25°C" (with standard degree symbol)
"""

import re
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Regex patterns (precompiled for performance)
# ─────────────────────────────────────────────────────────────────────────────

# Match temperature patterns like TC=25°C, TJ=25.5°C, TC=-55°C
# Note: do NOT add a trailing \b — it fails to match after ℃ (U+2103 DEGREE CELSIUS)
# because ℃ is not a \w character.
_TEMP_CONDITION_PATTERN = re.compile(
    r"""
    \b                              # word boundary before TC/TJ/Tj
    (TC|TJ|Tj)\s*[=:]\s*           # TC/TJ/Tj followed by = or :
    ([+-]?\d+\.?\d*)\s*            # integer or decimal, with optional sign
    \s*(°?[Cc]|℃|deg|C)            # optional spaces + degree symbol variants
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Normalize degree symbol to standard °C
_TEMP_UNIT_NORMALIZE = re.compile(r"°?[Cc]|℃|deg(?:\s|$)", re.IGNORECASE)


# ─────────────────────────────────────────────────────────────────────────────
# Normalization
# ─────────────────────────────────────────────────────────────────────────────

# Maps various degree representations to the standard "°C"
_DEGREE_NORMALIZE = {
    "℃": "°C",
    "°c": "°C",
    "°C": "°C",
    "C": "°C",
    "c": "°C",
    "℃": "°C",   # already handled but listed for completeness
}


def _normalize_temp_value(raw: str) -> str:
    """Normalize a temperature value to 'N°C' format."""
    raw = raw.strip()

    # Find numeric part
    m = re.match(r"^([+-]?\d+\.?\d*)", raw)
    if not m:
        return raw  # return as-is if no number found

    num = m.group(1)
    remainder = raw[m.end():].strip()

    # Normalize degree symbol
    if remainder:
        normalized = _DEGREE_NORMALIZE.get(remainder, remainder)
    else:
        normalized = "°C"

    return f"{num}{normalized}"


# ─────────────────────────────────────────────────────────────────────────────
# Main parsing function
# ─────────────────────────────────────────────────────────────────────────────

def parse_temperature_from_text(text: str) -> Optional[dict[str, str]]:
    """
    Extract temperature conditions from a heading or text string.

    Searches for patterns like:
        TC=25°C, TJ=25°C, TC=25.5°C, TJ=-55°C, TC=25 C, Tj=25 °C

    Returns a dict like {"TC": "25°C"} or {"TJ": "175°C"} if found,
    otherwise None.

    If multiple temperature conditions are found, returns the first one.
    (In practice, headings should only have one TC or TJ default.)
    """
    if not text:
        return None

    matches = _TEMP_CONDITION_PATTERN.findall(text)
    if not matches:
        return None

    # Take the first match (all groups)
    key_raw, num_raw, unit_raw = matches[0]

    # Normalize key to uppercase TC or TJ
    key = key_raw.upper()

    # Normalize value to standard format (e.g., "25°C")
    # Combine num_raw and unit_raw then normalize
    raw_value = (num_raw + (unit_raw or '')).strip()
    value = _normalize_temp_value(raw_value)

    return {key: value}


def extract_condition_from_heading(text: str) -> Optional[dict[str, str]]:
    """
    Extract temperature condition from a section/table heading.

    Specifically handles the "at TC=25°C unless otherwise specified" pattern
    commonly found in datasheet section headers.

    Returns {"TC": "25°C"} or {"TJ": "25°C"} if the heading contains
    a temperature specification, otherwise None.
    """
    return parse_temperature_from_text(text)


def has_temperature_condition(text: str) -> bool:
    """Return True if text contains a temperature condition (TC or TJ)."""
    if not text:
        return False
    return bool(_TEMP_CONDITION_PATTERN.search(text))


# ─────────────────────────────────────────────────────────────────────────────
# Condition extraction from parameter row cells
# ─────────────────────────────────────────────────────────────────────────────

def extract_temperature_from_cells(cells: list[str]) -> Optional[dict[str, str]]:
    """
    Try to extract a temperature condition from a row's cells.

    Checks the last non-empty cell first (typically the Test Conditions column),
    then falls back to searching all cells.

    Returns {"TC": "25°C"} or {"TJ": "25°C"} if found, else None.
    """
    if not cells:
        return None

    # Check last cell first (most likely to be conditions column)
    last_cell = cells[-1].strip()
    if last_cell:
        result = parse_temperature_from_text(last_cell)
        if result:
            return result

    # Search all cells
    for cell in cells:
        result = parse_temperature_from_text(cell)
        if result:
            return result

    return None


def extract_raw_condition_from_cells(cells: list[str]) -> Optional[str]:
    """
    Extract the raw condition string from a row's cells.

    Returns the last non-empty cell if it looks like a condition
    (contains = or is a temperature-like pattern).
    Returns None if no condition found.
    """
    if not cells:
        return None

    # Find last non-empty cell
    last_nonempty = None
    for cell in reversed(cells):
        if cell.strip():
            last_nonempty = cell.strip()
            break

    if not last_nonempty:
        return None

    # Check if it looks like a condition (contains =, or is a temp)
    if "=" in last_nonempty or has_temperature_condition(last_nonempty):
        return last_nonempty

    return None
