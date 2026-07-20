"""
page_heading_resolver.py — Phase 2B: Resolve page-level headings for Camelot tables.

Uses pdfplumber to extract text blocks with coordinates from each page of the PDF,
then matches heading-like text blocks to Camelot tables based on:
  1. Same page
  2. Heading is above the table
  3. Horizontal overlap with the table
  4. Vertical distance within threshold
  5. No closer table in between (uniqueness check)
  6. Heading text matches known section/table title patterns

Outputs structured heading context for each matched table, including:
  - table_title: combined title text
  - default_conditions: temperature conditions parsed from heading
  - sources: list of text blocks with their bboxes

This is a PURE LOCAL operation — no LLM, no API key.
"""

import re
from dataclasses import dataclass, field
from typing import Any

# pdfplumber is optional
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    pdfplumber = None


# ─────────────────────────────────────────────────────────────────────────────
# Dataclasses
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TextBlock:
    """A single text block extracted from pdfplumber."""
    text: str
    x0: float   # left edge
    top: float  # distance from top of page
    x1: float   # right edge
    bottom: float
    page_number: int

    @property
    def width(self) -> float:
        return self.x1 - self.x0


@dataclass
class HeadingGroup:
    """
    A group of TextBlocks that together form one logical heading.

    E.g., "Body Diode Characteristics" + "(at TJ=25°C unless otherwise specified)"
    """
    blocks: list[TextBlock]
    full_text: str           # combined text
    left: float              # leftmost x0
    right: float             # rightmost x1
    top: float               # topmost position (pdfplumber coords, from top)
    bottom: float            # bottommost position
    default_conditions: dict[str, str] = field(default_factory=dict)

    def horizontal_overlap_with(self, left: float, right: float) -> float:
        """Return horizontal overlap between heading and given range."""
        overlap_left = max(self.left, left)
        overlap_right = min(self.right, right)
        if overlap_right <= overlap_left:
            return 0.0
        return overlap_right - overlap_left

    @property
    def heading_width(self) -> float:
        return self.right - self.left


@dataclass
class TableGeometry:
    """Cached geometry for a Camelot table in pdfplumber coords."""
    page_number: int
    table_index: int
    top: float       # from top of page
    bottom: float    # from top of page
    left: float
    right: float


@dataclass
class HeadingAssignment:
    """A heading matched to a table."""
    page_number: int
    table_index: int
    heading_group: HeadingGroup
    vertical_distance: float   # heading bottom to table top (points)
    horizontal_overlap: float
    is_ambiguous: bool = False


@dataclass
class PageHeadingResult:
    """Result of page heading resolution for one page."""
    text_blocks_extracted: int = 0
    external_headings_detected: int = 0
    external_headings_assigned: int = 0
    ambiguous_external_headings: list[HeadingGroup] = field(default_factory=list)
    heading_to_table_assignments: list[HeadingAssignment] = field(default_factory=list)
    bbox_missing_tables: list[tuple[int, int]] = field(default_factory=list)
    coordinate_conversion_errors: int = 0


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_CONFIG = {
    "max_vertical_distance": 80.0,
    "minimum_horizontal_overlap": 0.3,
    "pdf_page_height": 841.92,
}


# ─────────────────────────────────────────────────────────────────────────────
# Heading detection patterns (same as row_classifier for consistency)
# ─────────────────────────────────────────────────────────────────────────────

_SECTION_PATTERNS = [
    (re.compile(r"(?i)^body\s*diode\s*characteristics", re.MULTILINE), "Body Diode Characteristics"),
    (re.compile(r"(?i)^static\s*characteristics", re.MULTILINE), "Static characteristics"),
    (re.compile(r"(?i)^dynamic\s*characteristics", re.MULTILINE), "Dynamic characteristics"),
    (re.compile(r"(?i)^switching\s*characteristics", re.MULTILINE), "Switching characteristics"),
    (re.compile(r"(?i)^absolute\s*maximum\s*ratings", re.MULTILINE), "Absolute Maximum Ratings"),
    (re.compile(r"(?i)^module\s*physical\s*characteristics", re.MULTILINE), "Module Physical Characteristics"),
    (re.compile(r"(?i)^source-drain\s*diode", re.MULTILINE), "Source-drain diode"),
    (re.compile(r"(?i)^gate\s*charge\s*characteristics", re.MULTILINE), "Gate charge characteristics"),
    (re.compile(r"(?i)^typical\s*performance", re.MULTILINE), "Typical Performance"),
    (re.compile(r"(?i)^output\s*characteristics", re.MULTILINE), "Output characteristics"),
    (re.compile(r"(?i)^transfer\s*characteristics", re.MULTILINE), "Transfer characteristics"),
    (re.compile(r"(?i)^mosfet\s*characteristics", re.MULTILINE), "MOSFET characteristics"),
]

_TABLE_TITLE_PATTERNS = [
    (re.compile(r"(?i)^key\s*parameters", re.MULTILINE), "Key Parameters"),
    (re.compile(r"(?i)^order\s*number", re.MULTILINE), "Order Number"),
    (re.compile(r"(?i)^marking", re.MULTILINE), "Marking"),
    (re.compile(r"(?i)^package\s*type", re.MULTILINE), "Package Type"),
]

# Pattern to detect parenthetical condition: "(at TJ=25°C unless otherwise specified)"
_COND_PARENTHETICAL = re.compile(
    r"\(\s*(?:at\s*)?(TJ|TC|T)\s*=\s*([^\)]+?)\s*(?:,\s*unless\s+otherwise\s+specified)?\s*\)",
    re.IGNORECASE
)

# Temperature value normalizer
_TEMP_VALUE = re.compile(r"^\s*([+-]?\d+(?:\.\d+)?)\s*°?\s*[Cc]?\s*$")

# Normalize temperature expressions where pdfplumber splits letters
# e.g., "T J =25" → "TJ=25" and "T C =25" → "TC=25"
_NORMALIZE_TEMP_LETTERS = re.compile(
    r'\b([TJTCtjtc])\s+([A-Za-z])\s*=\s*'
)


def _normalize_temp(value: str) -> str:
    """
    Normalize temperature value to 'N°C' format.

    Handles cases like "25℃", "25°C", "25 C", "25℃ unless otherwise specified".
    """
    value = value.strip()

    # Extract just the temperature part from values like "25℃ unless otherwise specified"
    # by looking for the degree symbol or temperature-related keywords
    temp_match = re.search(
        r'([+-]?\d+(?:\.\d+)?)\s*°?\s*[Cc]?',
        value
    )
    if temp_match:
        return f"{float(temp_match.group(1)):.0f}°C"

    # Fallback: try the original regex
    m = _TEMP_VALUE.match(value)
    if m:
        return f"{float(m.group(1)):.0f}°C"
    return value


def _parse_conditions_from_text(text: str) -> dict[str, str]:
    """
    Parse temperature conditions from heading text.

    Handles pdfplumber's letter-splitting issue where "TJ" appears as "T J"
    in the extracted text.
    """
    # Normalize temperature expressions: "T J =25" → "TJ=25"
    # This fixes pdfplumber splitting "TJ" into separate words
    normalized = _NORMALIZE_TEMP_LETTERS.sub(r'\1\2=', text)

    conditions = {}
    seen = set()

    # Try parenthetical first: "(at TJ=25°C unless otherwise specified)"
    m = _COND_PARENTHETICAL.search(normalized)
    if m:
        key = m.group(1).upper()
        if key == "T":
            key = "TJ"
        val = m.group(2).strip()
        conditions[key] = _normalize_temp(val)
        seen.add(key)

    # Also scan for standalone TC= or TJ= patterns
    for m2 in re.finditer(r"(?i)\b(TJ|TC|T)\s*=\s*([^\s;,\)]+)", normalized):
        key = m2.group(1).upper()
        if key == "T":
            key = "TJ"
        if key not in seen:
            conditions[key] = _normalize_temp(m2.group(2))
            seen.add(key)

    return conditions


def _is_heading_text(text: str) -> bool:
    """
    Check if text looks like a heading.

    Handles two cases:
    1. Full pattern match: text contains a full heading pattern
    2. Prefix match: text starts with a known heading prefix word.
       This handles cases where pdfplumber extracts heading words as separate blocks,
       so "Body" alone should be recognized as the start of
       "Body Diode Characteristics".
    """
    text = text.strip()
    if not text:
        return False

    # Check full pattern match (searches anywhere in text)
    for pat, _ in _SECTION_PATTERNS:
        if pat.search(text):
            return True
    for pat, _ in _TABLE_TITLE_PATTERNS:
        if pat.search(text):
            return True

    # Check prefix match — text starts with a known heading word.
    # This handles pdfplumber word-split headings where only the first
    # word is available for matching.
    text_lower = text.lower()
    _HEADING_START_WORDS = {
        # Section heading start words
        "body",
        "static",
        "dynamic",
        "switching",
        "absolute",
        "module",
        "source-drain",
        "gate",
        "typical",
        "output",
        "transfer",
        "mosfet",
        # Table title start words
        "key",
        "order",
        "package",
        "marking",
    }
    # Check if the FIRST WORD of text is a known heading start word
    first_word = text_lower.split()[0] if text_lower.split() else ""
    if first_word in _HEADING_START_WORDS:
        return True

    return False


# ─────────────────────────────────────────────────────────────────────────────
# Text extraction
# ─────────────────────────────────────────────────────────────────────────────

def _extract_page_blocks(pdf_path: str, page_number: int) -> list[TextBlock]:
    """Extract text blocks from one PDF page using pdfplumber."""
    if not PDFPLUMBER_AVAILABLE:
        return []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            page_idx = page_number - 1
            if page_idx < 0 or page_idx >= len(pdf.pages):
                return []
            page = pdf.pages[page_idx]
            words = page.extract_words()
            blocks = []
            for w in words:
                blocks.append(TextBlock(
                    text=w["text"],
                    x0=w["x0"],
                    top=w["top"],
                    x1=w["x1"],
                    bottom=w["bottom"],
                    page_number=page_number,
                ))
            return blocks
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Heading group building
# ─────────────────────────────────────────────────────────────────────────────

def _build_heading_groups(blocks: list[TextBlock]) -> list[HeadingGroup]:
    """
    Build heading groups from text blocks.

    Strategy:
    1. Find all blocks that look like headings (match section/table title patterns)
    2. When a heading is found, group ALL blocks on the same row (within 8 pts vertical)
       — this handles cases like "Body Diode Characteristics" split across 3 words
    3. Also include nearby condition blocks (starting with "(" or "at ")
    4. Combine into a HeadingGroup with merged text and conditions
    5. If combined text doesn't match any heading pattern, discard the group
    """
    if not blocks:
        return []

    sorted_blocks = sorted(blocks, key=lambda b: (b.page_number, b.top, b.x0))
    groups: list[HeadingGroup] = []
    i = 0
    n = len(sorted_blocks)

    while i < n:
        block = sorted_blocks[i]

        if not _is_heading_text(block.text):
            i += 1
            continue

        # Start a new group with this heading block
        group_blocks = [block]
        group_left = block.x0
        group_right = block.x1
        group_top = block.top
        group_bottom = block.bottom

        # Collect ALL blocks on the same row (within 8 pts vertical)
        # that are to the right of the heading block.
        # This handles multi-word headings like "Body Diode Characteristics"
        # where individual words might not match heading patterns.
        j = i + 1
        while j < n:
            next_block = sorted_blocks[j]
            if next_block.page_number != block.page_number:
                break
            # Must be on the same line (within 8 pts vertical)
            if abs(next_block.top - block.top) > 8:
                break
            # Must be to the right of current heading block
            if next_block.x0 < block.x1 - 5:
                j += 1
                continue

            cond_text = next_block.text.strip()

            # Condition blocks start with "(" or "at " — these end the heading
            if re.match(r"^\(|^at\s", cond_text, re.IGNORECASE):
                # Include the condition block as part of the heading group
                group_blocks.append(next_block)
                group_right = max(group_right, next_block.x1)
                group_bottom = max(group_bottom, next_block.bottom)
                # Continue looking for more condition-like blocks
                j += 1
                continue

            # For non-condition blocks:
            # Include them if they could be part of the heading text
            # (e.g., "Diode", "Characteristics" in "Body Diode Characteristics")
            # We include ALL such blocks — the final combined text will be validated
            group_blocks.append(next_block)
            group_right = max(group_right, next_block.x1)
            group_bottom = max(group_bottom, next_block.bottom)
            j += 1

        # Sort collected blocks by x0 and join their text
        group_blocks.sort(key=lambda b: b.x0)
        full_text = " ".join(b.text for b in group_blocks)
        conditions = _parse_conditions_from_text(full_text)

        # Only keep groups whose combined text matches a heading pattern
        # (This filters out accidental groupings of data blocks)
        if _is_heading_text(full_text):
            leftmost = min(b.x0 for b in group_blocks)
            rightmost = max(b.x1 for b in group_blocks)
            group = HeadingGroup(
                blocks=group_blocks,
                full_text=full_text,
                left=leftmost,
                right=rightmost,
                top=group_top,
                bottom=group_bottom,
                default_conditions=conditions,
            )
            groups.append(group)

        i = j  # Move past all blocks in this group

    return groups


# ─────────────────────────────────────────────────────────────────────────────
# Core resolution
# ─────────────────────────────────────────────────────────────────────────────

def resolve_page_headings(
    payload: Any,
    pdf_path: str,
    config: dict[str, Any] | None = None,
) -> dict[int, PageHeadingResult]:
    """
    Resolve page-level headings for all tables in the CamelotPayload.

    Args:
        payload: CamelotPayload (with table_bbox) or EnrichedPayload
                 (table_bbox forwarded from CamelotPayload)
        pdf_path: Path to the PDF file
        config: Resolution configuration

    Returns:
        Dict mapping page_number -> PageHeadingResult
    """
    if config is None:
        config = DEFAULT_CONFIG

    max_vert_dist = config.get("max_vertical_distance", 80.0)
    min_overlap_frac = config.get("minimum_horizontal_overlap", 0.3)
    pdf_page_height = config.get("pdf_page_height", 841.92)

    # Collect page numbers
    page_numbers = sorted(set(
        t.page_number
        for ep in payload.pages
        for t in ep.tables
    ))

    results: dict[int, PageHeadingResult] = {}

    for page_num in page_numbers:
        result = PageHeadingResult()
        results[page_num] = result

        # Step 1: Extract text blocks
        blocks = _extract_page_blocks(pdf_path, page_num)
        result.text_blocks_extracted = len(blocks)
        if not blocks:
            continue

        # Step 2: Build heading groups
        heading_groups = _build_heading_groups(blocks)
        result.external_headings_detected = len(heading_groups)

        # Step 3: Compute table geometries from table_bbox
        table_geometries: list[TableGeometry] = []
        bbox_missing: list[tuple[int, int]] = []

        for ep in payload.pages:
            if ep.page_number != page_num:
                continue
            for et in ep.tables:
                table_idx = et.table_index

                # Get table_bbox from CamelotTable or EnrichedTable
                table_bbox = getattr(et, "table_bbox", None)
                if table_bbox is None:
                    table_bbox = getattr(et, "_source_bbox", None)

                if table_bbox is None:
                    bbox_missing.append((page_num, table_idx))
                    # Use out-of-range geometry so no heading matches
                    ge = TableGeometry(
                        page_number=page_num,
                        table_index=table_idx,
                        top=9999.0,
                        bottom=10000.0,
                        left=0.0,
                        right=595.2,
                    )
                else:
                    x1, y1b, x2, y2b = table_bbox
                    top_pdf = pdf_page_height - float(y2b)
                    bottom_pdf = pdf_page_height - float(y1b)
                    ge = TableGeometry(
                        page_number=page_num,
                        table_index=table_idx,
                        top=float(top_pdf),
                        bottom=float(bottom_pdf),
                        left=float(x1),
                        right=float(x2),
                    )
                table_geometries.append(ge)

        result.bbox_missing_tables = bbox_missing

        if not table_geometries:
            continue

        # Step 4: Match headings to nearest table
        for hg in heading_groups:
            best: HeadingAssignment | None = None
            best_dist = float("inf")

            for ge in table_geometries:
                # Heading must be ABOVE the table
                if hg.bottom >= ge.top:
                    continue

                vert_dist = ge.top - hg.bottom
                if vert_dist > max_vert_dist:
                    continue

                if hg.heading_width <= 0:
                    continue
                overlap = hg.horizontal_overlap_with(ge.left, ge.right)
                if overlap / hg.heading_width < min_overlap_frac:
                    continue

                if vert_dist < best_dist:
                    best_dist = vert_dist
                    best = HeadingAssignment(
                        page_number=page_num,
                        table_index=ge.table_index,
                        heading_group=hg,
                        vertical_distance=vert_dist,
                        horizontal_overlap=overlap,
                    )

            if best:
                # Check for ambiguity (same heading assigned to another table)
                existing = [
                    a for a in result.heading_to_table_assignments
                    if a.heading_group is best.heading_group
                ]
                if existing:
                    for ex in existing:
                        ex.is_ambiguous = True
                    best.is_ambiguous = True
                    if best.heading_group not in result.ambiguous_external_headings:
                        result.ambiguous_external_headings.append(best.heading_group)
                else:
                    result.heading_to_table_assignments.append(best)
                    result.external_headings_assigned += 1

    return results


def get_table_page_heading(
    page_results: dict[int, PageHeadingResult],
    page_number: int,
    table_index: int,
) -> HeadingGroup | None:
    """
    Get the page-level heading for a specific table (unambiguous only).
    """
    if page_number not in page_results:
        return None
    result = page_results[page_number]
    for a in result.heading_to_table_assignments:
        if a.page_number == page_number and a.table_index == table_index:
            if not a.is_ambiguous:
                return a.heading_group
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Coordinate conversion helpers
# ─────────────────────────────────────────────────────────────────────────────

def camelot_bbox_to_pdfplumber(
    bbox: tuple[float, float, float, float],
    page_height: float = 841.92,
) -> tuple[float, float, float, float]:
    """
    Convert Camelot bbox (x1, y1_bottom, x2, y2_bottom) to
    pdfplumber coords (x1, top, x2, bottom) where origin is top-left.
    """
    x1, y1b, x2, y2b = bbox
    return (x1, page_height - y2b, x2, page_height - y1b)


def pdfplumber_bbox_to_camelot(
    bbox: tuple[float, float, float, float],
    page_height: float = 841.92,
) -> tuple[float, float, float, float]:
    """
    Convert pdfplumber bbox (x1, top, x2, bottom) to
    Camelot coords (x1, y1_bottom, x2, y2_bottom).
    """
    x1, top, x2, bottom = bbox
    return (x1, page_height - bottom, x2, page_height - top)
