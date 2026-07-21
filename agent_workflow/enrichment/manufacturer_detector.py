"""
Phase 3B: Document-Level Manufacturer Enrichment

Extracts manufacturer candidates from document-level text (page text, not table rows).
Does NOT modify any row data (raw_cells, raw_condition, row_id unchanged).

Evidence sources (priority order):
1. First page top text
2. Headers/footers
3. Website domains
4. General Description
5. Last page Disclaimer
6. Explicit company name text

No LLM calls, no OCR, no internet access.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import re
import unicodedata

# ─────────────────────────────────────────────────────────────────────────────
# Manufacturer Aliases (集中管理)
# ─────────────────────────────────────────────────────────────────────────────

MANUFACTURER_ALIASES: dict[str, dict] = {
    "AST Technology": {
        "exact_names": [
            "AST Technology",
            "AST TECHNOLOGY",
            "爱仕特科技",
            "AST Technology Co., Ltd.",
            "AST Technology Co., Ltd",
        ],
        "domains": [
            "astsic.com",
            "www.astsic.com",
        ],
        "abbreviation": "AST",
    },
    # Add more manufacturers here as needed
}

# Exact names lookup (for word-boundary matching)
_EXACT_NAME_LOOKUP: dict[str, str] = {}  # name_lower -> canonical
# Domains lookup (for domain extraction)
_DOMAIN_LOOKUP: dict[str, str] = {}  # domain_lower -> canonical

for canonical, info in MANUFACTURER_ALIASES.items():
    for name in info["exact_names"]:
        _EXACT_NAME_LOOKUP[name.lower()] = canonical
    for domain in info["domains"]:
        _DOMAIN_LOOKUP[domain.lower()] = canonical

# Combined for backward compatibility (but use separate lookups in logic)
_ALIAS_LOOKUP = {**_EXACT_NAME_LOOKUP, **_DOMAIN_LOOKUP}


# ─────────────────────────────────────────────────────────────────────────────
# Evidence source types
# ─────────────────────────────────────────────────────────────────────────────

class SourceType(Enum):
    EXACT_NAME = "exact_name"          # Full company name
    DOMAIN = "domain"                   # Website domain
    DISCLAIMER = "disclaimer"           # Disclaimer text
    LOGO_TEXT = "logo_text"             # Near logo
    ABBREVIATION = "abbreviation"       # Short form/abbreviation
    HEADER_FOOTER = "header_footer"      # Header/footer text
    PRODUCT_NAME = "product_name"        # Product name (weak evidence)


# ─────────────────────────────────────────────────────────────────────────────
# Confidence levels
# ─────────────────────────────────────────────────────────────────────────────

class Confidence(Enum):
    HIGH = "high"         # Exact name, domain, disclaimer
    MEDIUM = "medium"    # Logo text
    LOW = "low"          # Abbreviation only
    VERY_LOW = "very_low"  # Product name (almost nothing)


# ─────────────────────────────────────────────────────────────────────────────
# Evidence and Candidate dataclasses
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ManufacturerEvidence:
    value: str                    # Raw text found
    normalized_value: str          # Normalized value (for matching)
    canonical_name: str           # Canonical manufacturer name
    page_number: int              # Page where found
    source_type: str              # SourceType.value
    evidence_text: str            # Surrounding/context text
    confidence: str              # Confidence.value

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "normalized_value": self.normalized_value,
            "canonical_name": self.canonical_name,
            "page_number": self.page_number,
            "source_type": self.source_type,
            "evidence_text": self.evidence_text,
            "confidence": self.confidence,
        }


@dataclass
class ManufacturerCandidate:
    canonical_name: str
    evidences: list[ManufacturerEvidence] = field(default_factory=list)

    def add_evidence(self, evidence: ManufacturerEvidence) -> None:
        self.evidences.append(evidence)

    def to_dict(self) -> dict:
        return {
            "canonical_name": self.canonical_name,
            "evidences": [e.to_dict() for e in self.evidences],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Text normalization helpers
# ─────────────────────────────────────────────────────────────────────────────

def normalize_text(text: str) -> str:
    """Normalize text for comparison: NFKC + strip."""
    return unicodedata.normalize('NFKC', text).strip()


def normalize_for_matching(text: str) -> str:
    """Normalize text for case-insensitive matching."""
    return normalize_text(text).lower()


# ─────────────────────────────────────────────────────────────────────────────
# Blocked terms (must NOT be identified as manufacturer)
# ─────────────────────────────────────────────────────────────────────────────

BLOCKED_TERMS: set[str] = {
    # Part numbers
    "asc300n1200me3-x",
    "asc300n1200me3",
    "asc300",
    # Package types
    "me3",
    "module",
    # Product descriptions
    "silicon carbide mosfet module",
    "mosfet module",
    "sic mosfet module",
    # Order/marking related
    "order number",
    "marking",
    "package type",
    # Generic
    "manufactured",
    "manufacturer",
    "production",
}

# Pre-compute lowercase blocked terms for blocking check
_BLOCKED_SET: set[str] = {t.lower() for t in BLOCKED_TERMS}


def is_blocked_term(text: str) -> bool:
    """Check if text is a blocked term (not a manufacturer)."""
    normalized = normalize_for_matching(text)
    # Direct match
    if normalized in _BLOCKED_SET:
        return True
    # Check if blocked term is a substring (but allow company names that contain blocked terms)
    for blocked in _BLOCKED_SET:
        if blocked in normalized and len(normalized) < len(blocked) + 3:
            return True
    return False


def is_likely_part_number(text: str) -> bool:
    """Heuristic: if text looks like a part number, it's not a manufacturer.

    A text is likely a part number ONLY if:
    - It contains digits AND is short (< 20 chars)
    - OR it's ALL uppercase/letters/digits/hyphens with no spaces and starts with letters+digits

    But NOT if it contains URLs (www., http), emails (@), or multiple distinct content types.
    """
    # If text contains URL indicators, it's not just a part number
    if 'www.' in text.lower() or 'http' in text.lower() or '@' in text:
        return False

    # Contains digits and is short - likely part number
    if re.search(r'\d', text) and len(text) < 20:
        return True

    # All caps with mixed letters and numbers, no spaces, starts with letter+digits - likely PN
    # But NOT if it contains other separators like / or multiple words
    if (re.match(r'^[A-Z]{2,}\d+[A-Z0-9\-]*$', text) and
        len(text) < 25 and
        ' ' not in text):
        return True

    return False


# ─────────────────────────────────────────────────────────────────────────────
# Domain extraction from text
# ─────────────────────────────────────────────────────────────────────────────

DOMAIN_PATTERN = re.compile(
    r'(?:https?://)?(?:www\.)?([a-zA-Z0-9][-a-zA-Z0-9]*(?:\.[a-zA-Z]{2,})+)/?',
    re.IGNORECASE
)


def extract_domains(text: str) -> list[str]:
    """Extract domain names from text."""
    matches = DOMAIN_PATTERN.findall(text)
    return [m.lower() for m in matches if len(m) > 3]


# ─────────────────────────────────────────────────────────────────────────────
# Manufacturer detection from text
# ─────────────────────────────────────────────────────────────────────────────

def find_manufacturer_in_text(
    text: str,
    page_number: int,
    source_type: str = "general"
) -> list[ManufacturerEvidence]:
    """
    Find manufacturer evidence in a block of text.

    Returns list of evidence found (may be empty).
    """
    evidences = []
    normalized_text = normalize_for_matching(text)

    # Skip blocked terms
    if is_blocked_term(text):
        return []

    # Skip likely part numbers
    if is_likely_part_number(text):
        return []

    # 1. Check exact names (highest priority) - only check exact name keys
    for name_lower, canonical in _EXACT_NAME_LOOKUP.items():
        if name_lower in normalized_text:
            # Verify word boundary - don't match "FAST" in "FASCIST"
            # Use simple approach: check if name is surrounded by non-alphanumeric
            pattern = r'(?:^|[\s\-_,;|()])(%s)(?:$|[\s\-_,;|()])' % re.escape(name_lower)
            if re.search(pattern, normalized_text, re.IGNORECASE):
                evidences.append(ManufacturerEvidence(
                    value=name_lower,
                    normalized_value=canonical,
                    canonical_name=canonical,
                    page_number=page_number,
                    source_type=SourceType.EXACT_NAME.value,
                    evidence_text=text.strip(),
                    confidence=Confidence.HIGH.value,
                ))

    # 2. Check domains - only check domain keys
    domains = extract_domains(text)
    for domain in domains:
        if domain in _DOMAIN_LOOKUP:
            canonical = _DOMAIN_LOOKUP[domain]
            evidences.append(ManufacturerEvidence(
                value=domain,
                normalized_value=canonical,
                canonical_name=canonical,
                page_number=page_number,
                source_type=SourceType.DOMAIN.value,
                evidence_text=text.strip(),
                confidence=Confidence.HIGH.value,
            ))

    # 3. Check abbreviations (LOW confidence, only if standalone)
    # This is a weak check - only match if the text IS the abbreviation
    for canonical, info in MANUFACTURER_ALIASES.items():
        abbrev = info.get("abbreviation", "").lower()
        if abbrev and abbrev == normalized_text:
            # Only add if no other evidence found
            if not evidences:
                evidences.append(ManufacturerEvidence(
                    value=abbrev.upper(),
                    normalized_value=canonical,
                    canonical_name=canonical,
                    page_number=page_number,
                    source_type=SourceType.ABBREVIATION.value,
                    evidence_text=text.strip(),
                    confidence=Confidence.LOW.value,
                ))

    return evidences


# ─────────────────────────────────────────────────────────────────────────────
# Page text cache (避免重复打开 PDF)
# Cache key includes file path + size + mtime_ns to detect file changes
# ─────────────────────────────────────────────────────────────────────────────

# Cache structure: {cache_key: page_texts}
# cache_key = (abs_path, file_size, mtime_ns)
_page_text_cache: dict[tuple[str, int, int], dict[int, list[str]]] = {}


def _get_cache_key(pdf_path: str) -> tuple[str, int, int]:
    """Compute cache key including file metadata for invalidation."""
    import os
    abs_path = os.path.abspath(pdf_path)
    stat = os.stat(abs_path)
    return (abs_path, stat.st_size, stat.st_mtime_ns)


def get_page_texts(pdf_path: str) -> dict[int, list[str]]:
    """
    Get all text from each page of the PDF.
    Uses caching to avoid re-opening the PDF multiple times.
    Cache key includes file path + size + mtime_ns to detect file changes.

    Returns: {page_number: [text_block1, text_block2, ...]}
    Returns empty dict if file doesn't exist.
    """
    try:
        cache_key = _get_cache_key(pdf_path)
    except (FileNotFoundError, OSError):
        return {}

    if cache_key in _page_text_cache:
        return _page_text_cache[cache_key]

    # Import here to avoid hard dependency
    try:
        import pdfplumber
    except ImportError:
        return {}

    page_texts: dict[int, list[str]] = {}

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                blocks = []
                # Extract words and group them into text blocks
                words = page.extract_words()
                # Group words by approximate Y position (same line)
                current_line: list[dict] = []
                last_top = None

                for w in words:
                    if last_top is None or abs(w["top"] - last_top) < 5:
                        current_line.append(w)
                    else:
                        if current_line:
                            # Sort by x position and join
                            sorted_words = sorted(current_line, key=lambda x: x["x0"])
                            line_text = " ".join(w["text"] for w in sorted_words)
                            blocks.append(line_text)
                        current_line = [w]
                    last_top = w["top"]

                # Don't forget the last line
                if current_line:
                    sorted_words = sorted(current_line, key=lambda x: x["x0"])
                    line_text = " ".join(w["text"] for w in sorted_words)
                    blocks.append(line_text)

                page_texts[page_num] = blocks
    except Exception:
        return {}

    _page_text_cache[cache_key] = page_texts
    return page_texts


def clear_page_text_cache() -> None:
    """Clear the page text cache. Useful for testing and memory management."""
    global _page_text_cache
    _page_text_cache.clear()


# ─────────────────────────────────────────────────────────────────────────────
# Document-level manufacturer extraction
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ManufacturerResult:
    status: str              # "resolved", "ambiguous", "missing"
    canonical_value: Optional[str]  # null if ambiguous or missing
    candidates: list[ManufacturerCandidate] = field(default_factory=list)
    quality_flags: list[str] = field(default_factory=list)

    # Diagnostic fields for evidence analysis
    evidence_count: int = 0          # Total raw evidences (including duplicates)
    unique_evidence_count: int = 0   # Unique evidence items
    independent_source_types: list[str] = field(default_factory=list)  # Unique source_types
    pages_found: list[int] = field(default_factory=list)  # Unique pages with evidence

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "canonical_value": self.canonical_value,
            "candidates": [c.to_dict() for c in self.candidates],
            "quality_flags": self.quality_flags,
            # Diagnostic fields
            "evidence_count": self.evidence_count,
            "unique_evidence_count": self.unique_evidence_count,
            "independent_source_types": self.independent_source_types,
            "pages_found": sorted(self.pages_found),
        }


def extract_manufacturer(pdf_path: str) -> ManufacturerResult:
    """
    Extract manufacturer from document-level text.

    Searches in priority order:
    1. Page 1 (first page - most important)
    2. All pages (for domain, disclaimer, etc.)

    Returns ManufacturerResult with candidates, status, and canonical_value.
    """
    page_texts = get_page_texts(pdf_path)

    if not page_texts:
        return ManufacturerResult(
            status="missing",
            canonical_value=None,
            candidates=[],
            quality_flags=["page_text_extraction_failed"],
            evidence_count=0,
            unique_evidence_count=0,
            independent_source_types=[],
            pages_found=[],
        )

    # Collect all evidences
    all_evidences: list[ManufacturerEvidence] = []

    # Search order: page 1 first (most important), then other pages
    page_order = [1] + [p for p in sorted(page_texts.keys()) if p != 1]

    for page_num in page_order:
        blocks = page_texts.get(page_num, [])

        # Determine source type based on page
        if page_num == 1:
            source_type = "first_page"
        elif page_num == len(page_texts):
            source_type = "last_page"  # Likely disclaimer
        else:
            source_type = "general"

        for block in blocks:
            evidences = find_manufacturer_in_text(block, page_num, source_type)
            all_evidences.extend(evidences)

    if not all_evidences:
        return ManufacturerResult(
            status="missing",
            canonical_value=None,
            candidates=[],
            quality_flags=["no_manufacturer_evidence"],
            evidence_count=0,
            unique_evidence_count=0,
            independent_source_types=[],
            pages_found=[],
        )

    # Group evidences by canonical name
    candidate_map: dict[str, ManufacturerCandidate] = {}
    for ev in all_evidences:
        if ev.canonical_name not in candidate_map:
            candidate_map[ev.canonical_name] = ManufacturerCandidate(
                canonical_name=ev.canonical_name
            )
        candidate_map[ev.canonical_name].add_evidence(ev)

    candidates = list(candidate_map.values())

    # Compute diagnostic statistics
    evidence_count = len(all_evidences)
    unique_evidences = []
    for ev in all_evidences:
        key = (ev.normalized_value, ev.source_type, ev.page_number)
        if key not in [ (u.normalized_value, u.source_type, u.page_number) for u in unique_evidences ]:
            unique_evidences.append(ev)
    unique_evidence_count = len(unique_evidences)
    independent_source_types = sorted(set(e.source_type for e in all_evidences))
    pages_with_evidence = sorted(set(e.page_number for e in all_evidences))

    # Determine status
    quality_flags: list[str] = []

    # Check for explicit full company name (exact_name) - HIGHEST priority
    has_exact_name = any(
        e.source_type == SourceType.EXACT_NAME.value and e.confidence == Confidence.HIGH.value
        for e in all_evidences
    )

    # Check for multiple meaningful evidence types (not just same domain repeated)
    # Count unique (source_type, confidence_level) pairs as different evidence types
    unique_evidence_types = set()
    for ev in all_evidences:
        if ev.confidence == Confidence.HIGH.value:
            unique_evidence_types.add((ev.source_type, ev.confidence))
    has_meaningful_multi_source = len(unique_evidence_types) >= 2

    # Check for weak evidence only
    has_weak_only = all(
        e.confidence in (Confidence.LOW.value, Confidence.VERY_LOW.value)
        for e in all_evidences
    )

    if has_weak_only:
        quality_flags.append("weak_abbreviation_only")
        # Still resolved if we have a canonical name, but mark as weak
        canonical = candidates[0].canonical_name if candidates else None
        return ManufacturerResult(
            status="resolved",  # Still resolved, but weak
            canonical_value=canonical,
            candidates=candidates,
            quality_flags=quality_flags,
            evidence_count=evidence_count,
            unique_evidence_count=unique_evidence_count,
            independent_source_types=independent_source_types,
            pages_found=pages_with_evidence,
        )

    if len(candidates) > 1:
        # Multiple different manufacturers - ambiguous
        quality_flags.append("multiple_manufacturer_candidates")
        return ManufacturerResult(
            status="ambiguous",
            canonical_value=None,
            candidates=candidates,
            quality_flags=quality_flags,
            evidence_count=evidence_count,
            unique_evidence_count=unique_evidence_count,
            independent_source_types=independent_source_types,
            pages_found=pages_with_evidence,
        )

    # Single manufacturer - check resolved conditions
    # RESOLVED if: has explicit full company name (exact_name) OR multiple meaningful evidence types
    if has_exact_name:
        quality_flags.append("explicit_company_name_found")
    elif has_meaningful_multi_source:
        quality_flags.append("multiple_meaningful_evidence_types")
    else:
        # Not enough evidence to resolve
        return ManufacturerResult(
            status="missing",
            canonical_value=None,
            candidates=candidates,
            quality_flags=quality_flags + ["insufficient_evidence"],
            evidence_count=evidence_count,
            unique_evidence_count=unique_evidence_count,
            independent_source_types=independent_source_types,
            pages_found=pages_with_evidence,
        )

    return ManufacturerResult(
        status="resolved",
        canonical_value=candidates[0].canonical_name,
        candidates=candidates,
        quality_flags=quality_flags,
        evidence_count=evidence_count,
        unique_evidence_count=unique_evidence_count,
        independent_source_types=independent_source_types,
        pages_found=pages_with_evidence,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Quick test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        result = extract_manufacturer(pdf_path)
        print(f"Status: {result.status}")
        print(f"Canonical: {result.canonical_value}")
        print(f"Candidates: {len(result.candidates)}")
        print(f"Quality flags: {result.quality_flags}")
        for c in result.candidates:
            print(f"  - {c.canonical_name}: {len(c.evidences)} evidences")
            for e in c.evidences:
                print(f"      [{e.source_type}] p{e.page_number}: {e.evidence_text[:50]}...")
