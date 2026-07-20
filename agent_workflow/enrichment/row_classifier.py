"""
row_classifier.py — Row-type classification.

Phase 1: Conservative row classification without context.
Phase 2A: Handles Camelot-split cells and distinguishes TABLE_TITLE from SECTION_TITLE.

Classification is conservative: when in doubt, classify as UNKNOWN.
"""

import re
from typing import Optional

from .models import RowType


# ─────────────────────────────────────────────────────────────────────────────
# Classification keywords & patterns
# ─────────────────────────────────────────────────────────────────────────────

# Column header keywords — any of these strongly suggest a column header row
_COLUMN_HEADER_KEYWORDS = [
    "symbol",
    "parameter",
    "min",
    "max",
    "typ",
    "unit",
    "conditions",
    "test conditions",
    "values",
]

# TABLE_TITLE patterns — module/parameter-group level titles.
# These phrases describe a parameter GROUP, not a characteristic type.
_TABLE_TITLE_PATTERNS = [
    re.compile(r"\bmosfet\s+characteristics\b", re.IGNORECASE),
    re.compile(r"\bmodule\s+physical\s+characteristics\b", re.IGNORECASE),
    re.compile(r"\bswitching\s+characteristics\b", re.IGNORECASE),
    re.compile(r"\bgate\s+drive\s+characteristics\b", re.IGNORECASE),
    re.compile(r"\bprotection\s+characteristics\b", re.IGNORECASE),
    re.compile(r"\border\s+number\b", re.IGNORECASE),
    re.compile(r"\bkey\s+parameters?\b", re.IGNORECASE),
    re.compile(r"\bmaximum\s+ratings?\b", re.IGNORECASE),
]

# SECTION_TITLE patterns — characteristic-TYPE level headers.
# These phrases describe the TYPE of characteristics (static, dynamic, etc.).
# These can appear as Camelot-split text (e.g., "ody Diode Characteristics").
_SECTION_TITLE_PATTERNS = [
    re.compile(r"static\s+characteristics", re.IGNORECASE),
    re.compile(r"dynamic\s+characteristics", re.IGNORECASE),
    re.compile(r"switching\s+characteristics", re.IGNORECASE),
    re.compile(r"absolute\s+maximum\s+ratings?", re.IGNORECASE),
    re.compile(r"body\s*diode\s*characteristics", re.IGNORECASE),
    re.compile(r"source-drain\s*diode", re.IGNORECASE),
    re.compile(r"electrical\s+characteristics", re.IGNORECASE),
    re.compile(r"thermal\s+characteristics", re.IGNORECASE),
    re.compile(r"module\s+physical\s+characteristics", re.IGNORECASE),
    re.compile(r"unless\s+otherwise\s+specified", re.IGNORECASE),
]

# Parameter row heuristics: must have a non-empty first cell (symbol) AND
# at least one value-like cell (numeric or dash)
_VALUE_PATTERNS = [
    re.compile(r"^-?[\d.\s]+$"),          # pure numbers / dashes
    re.compile(r"^\s*\d+\.?\d*\s*[mμpnkMGT]?[VAAFΩHNOCS]+.*$", re.IGNORECASE),  # number + unit
]

# Separator patterns: rows that are all dashes, equals, or whitespace
_SEPARATOR_PATTERNS = [
    re.compile(r"^[\-=_~·•]{3,}$"),        # 3+ consecutive separators
    re.compile(r"^\s*[\-=_~·•]+\s*$"),     # only separators and whitespace
]

# Camelot lattice sometimes splits a title across cells where the first cell
# is a single garbage character (e.g., "B" + "ody Diode Characteristics").
_CAMELOT_BROKEN_PREFIX = re.compile(r"^[A-Za-z0-9]$")


# ─────────────────────────────────────────────────────────────────────────────
# RowClassifier
# ─────────────────────────────────────────────────────────────────────────────

class RowClassifier:
    """
    Conservative row-type classifier.

    Phase 1: Classify rows without context.
    Phase 2A: Also distinguish TABLE_TITLE from SECTION_TITLE and handle
    Camelot-split cells.
    """

    def classify(self, row_cells: list[str]) -> RowType:
        """
        Classify a single row based on its cell content.

        Phase 2A logic:
        1. EMPTY / SEPARATOR / COLUMN_HEADER — same as Phase 1
        2. Join ALL cells and check TABLE_TITLE patterns first
        3. Check SECTION_TITLE patterns in full joined text
        4. Fallback: first non-trivial cell for title patterns
        5. PARAMETER
        6. UNKNOWN

        Args:
            row_cells: List of cell strings from CamelotPayload.

        Returns:
            RowType enum value.
        """
        if not row_cells:
            return RowType.UNKNOWN

        # 1. EMPTY — all cells are empty or whitespace-only
        if self._is_empty(row_cells):
            return RowType.EMPTY

        # 2. SEPARATOR — row is all dashes / separators
        if self._is_separator(row_cells):
            return RowType.SEPARATOR

        # 3. COLUMN_HEADER — row contains multiple column header keywords
        if self._is_column_header(row_cells):
            return RowType.COLUMN_HEADER

        # ── Phase 2A: Camelot-split cell handling ────────────────────────────
        # Join ALL cells (including Camelot-split garbage) to check patterns.
        # This handles broken rows like ['B', 'ody Diode Characteristics...']
        joined_all = " ".join(c for c in row_cells if c.strip())

        # 4a. SECTION_TITLE FIRST — "characteristic"/"rating" phrases are usually
        # section titles. "Switching characteristics" belongs to SECTION_TITLE.
        if self._matches_section_title_pattern(joined_all):
            return RowType.SECTION_TITLE

        # 4b. TABLE_TITLE check on full joined text (after section patterns)
        if self._matches_table_title_pattern(joined_all):
            return RowType.TABLE_TITLE

        # ── Fallback: non-trivial cells ─────────────────────────────
        non_trivial = [
            c.strip() for c in row_cells
            if c.strip() and not self._is_camelot_broken_char(c)
        ]

        # 5a. TABLE_TITLE: first non-trivial cell matching a known table title
        # (also handles single-cell rows like ['Order Number'])
        if non_trivial and self._matches_table_title_pattern(non_trivial[0]):
            return RowType.TABLE_TITLE

        # 5b. SECTION_TITLE: first non-trivial cell matches section patterns
        if non_trivial and self._matches_section_title_pattern(non_trivial[0]):
            return RowType.SECTION_TITLE

        # 6. PARAMETER — conservative check for a data row
        if self._is_parameter(row_cells):
            return RowType.PARAMETER

        # 7. UNKNOWN — cannot reliably classify
        return RowType.UNKNOWN

    # ─────────────────────────────────────────────────────────────────────
    # Individual checks
    # ─────────────────────────────────────────────────────────────────────

    def _is_empty(self, cells: list[str]) -> bool:
        """All cells are empty or whitespace-only."""
        return all(not c.strip() for c in cells)

    def _is_separator(self, cells: list[str]) -> bool:
        """
        Row consists only of separator characters and whitespace.
        Matches: '---', '===', '___', '•••', etc.
        """
        non_empty = [c.strip() for c in cells if c.strip()]
        if not non_empty:
            return False
        return all(
            _SEPARATOR_PATTERNS[0].match(c) or _SEPARATOR_PATTERNS[1].match(c)
            for c in non_empty
        )

    def _is_column_header(self, cells: list[str]) -> bool:
        """
        Row contains multiple column-header keywords.
        E.g., ['Symbol', 'Parameter', 'Min.', 'Typ.', 'Max.', 'Unit', 'Test Conditions']
        """
        hits = 0
        joined = " ".join(c.lower() for c in cells)
        for kw in _COLUMN_HEADER_KEYWORDS:
            if kw in joined:
                hits += 1
        return hits >= 3

    def _matches_table_title_pattern(self, text: str) -> bool:
        """Check if text matches any TABLE_TITLE pattern."""
        if not text:
            return False
        for pattern in _TABLE_TITLE_PATTERNS:
            if pattern.search(text):
                return True
        return False

    def _matches_section_title_pattern(self, text: str) -> bool:
        """Check if text matches any SECTION_TITLE pattern."""
        if not text:
            return False
        for pattern in _SECTION_TITLE_PATTERNS:
            if pattern.search(text):
                return True
        return False

    def _is_valid_table_title_text(self, text: str) -> bool:
        """
        Check if a single-cell text is a valid TABLE_TITLE.

        Phase 2A is more conservative than Phase 1:
        - Requires clear title keyword match
        - Does NOT use "single non-empty cell + len < 30" as sufficient condition
        - Rejects Camelot garbage characters
        """
        if not text or len(text) >= 40:
            return False
        if self._looks_like_parameter_text(text):
            return False
        if self._matches_table_title_pattern(text):
            return True
        # Camelot broken single char: 'B', 'A', etc. → not a table title
        if len(text) == 1 and self._is_camelot_broken_char(text):
            return False
        return False

    def _is_camelot_broken_char(self, text: str) -> bool:
        """Check if text is a single Camelot lattice broken character."""
        return bool(_CAMELOT_BROKEN_PREFIX.match(text.strip()))

    def _is_parameter(self, cells: list[str]) -> bool:
        """
        Conservative check for a data row with parameter + value.

        Criteria:
        - First cell (symbol column) is non-empty
        - First cell is NOT a Camelot broken char
        - At least one cell contains a value-like pattern
        """
        if not cells:
            return False
        symbol_cell = cells[0].strip()
        if not symbol_cell:
            return False
        if self._is_camelot_broken_char(symbol_cell):
            return False
        non_empty = [c.strip() for c in cells if c.strip()]
        if len(non_empty) < 2:
            return False
        has_value = any(self._looks_like_value(c) for c in cells)
        return has_value

    def _looks_like_value(self, cell: str) -> bool:
        """Check if a cell looks like a numeric value or value+unit."""
        cell = cell.strip()
        if not cell:
            return False
        if cell == "-":
            return True
        for pattern in _VALUE_PATTERNS:
            if pattern.match(cell):
                return True
        return False

    def _looks_like_parameter_text(self, text: str) -> bool:
        """
        Check if text looks like a parameter name rather than a title.
        E.g., 'RDS(on)' looks like a parameter; 'Key Parameters' looks like a title.
        """
        if re.search(r"\(.*\)", text):          # has parentheses — likely symbol
            return True
        if re.search(r"[Ωμπαβ]", text):         # has greek/special chars
            return True
        # Numbers in the middle suggest values; part numbers are ok
        if re.search(r"\d+[A-Za-z]", text) and not re.search(r"\d{4,}", text):
            if re.match(r"^[A-Z]{2,}\d+[A-Z0-9-]+$", text):
                return False  # part number
            return True
        return False
