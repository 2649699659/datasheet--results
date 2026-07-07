"""
Generic text-based fallback for mechanical/isolation parameters.

When pdfplumber table extraction loses section headers (e.g., "Clearance Distance"
parsed as "R 1-3"), this module extracts relevant text blocks from page_text
to recover the heading context.

This is a GENERIC fallback - no manufacturer-specific logic.
"""
import re
from typing import Optional


# Generic mechanical/isolation heading patterns to look for
HEADING_PATTERNS = [
    # Primary headings
    r"(?:Clearance\s*Distance|Clearance)",
    r"(?:Creepage\s*Distance|Creepage)",
    r"(?:Isolation\s*Voltage|Isolation\s*Characteristics|Dielectric\s*Strength)",
    r"(?:Weight|Module\s*Weight)",
    r"(?:Mounting\s*Torque)",
    r"(?:Stray\s*Inductance|LStray)",
    r"(?:Package\s*Resistance|R\s*\(package\))",
    r"(?:Module\s*Physical\s*Characteristics|Physical\s*Characteristics)",
    r"(?:Mechanical\s*Characteristics|Mechanical\s*Specifications)",
    r"(?:Isolation\s*Characteristics)",
    r"(?:Terminal\s*Torque)",
    r"(?:Storage\s*Temperature|Temperature\s*Range)",
    r"(?:Operating\s*Temperature)",
    r"(?:Relative\s*Humidity)",
    r"(?:Altitude)",
    r"(?:Vibration)",
    r"(?:Shock)",
    r"(?:Lead\s*Free|Note\s*About\s*Halogens)",
    r"(?:MSL|Moisture\s*Sensitivity)",
    # Sub-row headings (often lost in table extraction)
    r"(?:Terminal\s*to\s*Terminal|Terminal\s*-\s*Terminal)",
    r"(?:Terminal\s*to\s*Baseplate|Terminal\s*-\s*Baseplate)",
    r"(?:Surface\s*to\s*Surface|Surface\s*-\s*Surface)",
    r"(?:Comparative\s*Tracking\s*Index|CTI)",
]

# Window size: how many characters before/after heading to include
TEXT_WINDOW = 250


def _find_heading_positions(text: str, heading: str) -> list[tuple[int, int]]:
    """
    Find all occurrences of a heading in text.
    Returns list of (start, end) positions.
    """
    positions = []
    pattern = re.compile(heading, re.IGNORECASE)
    for m in pattern.finditer(text):
        positions.append((m.start(), m.end()))
    return positions


def _extract_text_window(text: str, position: int, heading_len: int, window: int = TEXT_WINDOW) -> str:
    """
    Extract a text window around a heading position.
    Returns text AFTER the heading (not before, to avoid bleeding into previous section).
    If after-text is too short, also include some text before.
    """
    heading_end = position + heading_len
    end_pos = min(len(text), heading_end + window)
    
    after = text[heading_end:end_pos]
    after = re.sub(r"\s+", " ", after).strip()
    
    # If after is too short, also include some text before heading
    if len(after) < 50:
        start = max(0, position - 80)
        before = text[start:position]
        before = re.sub(r"\s+", " ", before).strip()
        after = f"{before} {after}".strip()
    
    return after


def _looks_like_mechanical_page(page_text: str) -> bool:
    """
    Heuristic: does this page text likely contain mechanical/isolation parameters?
    """
    mechanical_keywords = [
        "clearance", "creepage", "mounting", "torque", "weight",
        "isolation", "visol", " dielectric", "altitude", "vibration",
        "shock", "storage temperature", "relative humidity",
        "mechanical", "physical characteristic", "terminal to terminal",
        "terminal to baseplate", "surface to surface",
    ]
    text_lower = page_text.lower()
    matches = sum(1 for kw in mechanical_keywords if kw in text_lower)
    return matches >= 2


def extract_relevant_text_blocks(page_text: str, page_num: int = 1) -> list[dict]:
    """
    Extract text blocks from page_text that contain mechanical/isolation parameters.
    
    This is used when pdfplumber table extraction loses section headers.
    The LLM can use these text blocks to recover the heading context.
    
    Args:
        page_text: Raw text from the page (not formatted tables)
        page_num: Page number for source tracking
    
    Returns:
        List of blocks, each with:
        {
            "heading": "Clearance Distance",
            "text": "...local text window...",
            "page": 3,
            "source": "page_text_fallback"
        }
    """
    if not page_text or len(page_text) < 50:
        return []
    
    blocks = []
    
    for heading_pattern in HEADING_PATTERNS:
        positions = _find_heading_positions(page_text, heading_pattern)
        
        for start, end in positions:
            # Extract the matched heading text
            matched_heading = page_text[start:end].strip()
            
            # Normalize heading to canonical form
            canonical = _normalize_heading(matched_heading)
            if not canonical:
                continue
            
            # Extract text window
            text_window = _extract_text_window(page_text, start, len(matched_heading))
            
            # Skip if the window is too short (heading alone, no data)
            if len(text_window) < 30:
                continue
            
            # Avoid duplicate blocks for the same heading
            if any(b["heading"] == canonical for b in blocks):
                continue
            
            blocks.append({
                "heading": canonical,
                "text": text_window,
                "page": page_num,
                "source": "page_text_fallback",
            })
    
    return blocks


def _normalize_heading(text: str) -> Optional[str]:
    """
    Normalize a matched heading to a canonical parameter name.
    """
    text = text.strip()
    text_lower = text.lower()
    
    # Clearance
    if "clearance" in text_lower:
        if "distance" in text_lower:
            return "Clearance Distance"
        return "Clearance Distance"
    
    # Creepage
    if "creepage" in text_lower:
        if "distance" in text_lower:
            return "Creepage Distance"
        return "Creepage Distance"
    
    # Isolation Voltage
    if "isolation" in text_lower or "dielectric" in text_lower:
        return "Isolation Voltage"
    if "visol" in text_lower:
        return "Isolation Voltage"
    
    # Weight
    if "weight" in text_lower:
        return "Weight"
    
    # Mounting Torque
    if "mounting torque" in text_lower or "terminal torque" in text_lower:
        return "Mounting Torque"
    
    # Stray Inductance
    if "stray inductance" in text_lower or "lstray" in text_lower:
        return "Stray Inductance"
    
    # Package Resistance
    if "package resistance" in text_lower or "r (package)" in text_lower:
        return "Package Resistance"
    
    # Terminal to Terminal
    if "terminal to terminal" in text_lower or "terminal - terminal" in text_lower:
        return "Clearance Distance (Terminal to Terminal)"
    
    # Terminal to Baseplate
    if "terminal to baseplate" in text_lower or "terminal - baseplate" in text_lower:
        return "Clearance Distance (Terminal to Baseplate)"
    
    # Surface to Surface
    if "surface to surface" in text_lower or "surface - surface" in text_lower:
        return "Creepage Distance"
    
    # Mechanical / Physical Characteristics
    if "mechanical characteristic" in text_lower:
        return "Mechanical Characteristics"
    if "physical characteristic" in text_lower:
        return "Physical Characteristics"
    
    # Storage / Operating Temperature
    if "storage temperature" in text_lower:
        return "Storage Temperature"
    if "operating temperature" in text_lower:
        return "Operating Temperature"
    
    # Relative Humidity
    if "relative humidity" in text_lower:
        return "Relative Humidity"
    
    # CTI
    if "comparative tracking" in text_lower or "cti" in text_lower:
        return "Comparative Tracking Index"
    
    # Vibration / Shock
    if "vibration" in text_lower:
        return "Vibration"
    if "shock" in text_lower:
        return "Shock"
    
    return None


def format_text_blocks_for_prompt(blocks: list[dict]) -> str:
    """
    Format text blocks as markdown sections for inclusion in LLM prompt.
    """
    if not blocks:
        return ""
    
    parts = ["## TEXT FALLBACK BLOCKS (Section Context from Page Text)"]
    parts.append("")
    
    for block in blocks:
        parts.append(f"### {block['heading']}")
        parts.append("")
        parts.append(block["text"])
        parts.append("")
        parts.append(f"[Source: {block['source']}, Page {block['page']}]")
        parts.append("")
        parts.append("---")
        parts.append("")
    
    return "\n".join(parts)


if __name__ == "__main__":
    # Simple test
    test_text = """
    4.2.4 Clearance Distance
        
    All dimensions in mm.
    Terminal to Terminal: 9 mm minimum
    Terminal to Baseplate: 30 mm minimum
    
    4.2.5 Creepage Distance
    
    Surface to Surface measurement.
    Terminal to Terminal: 30 mm minimum
    Terminal to Baseplate: 40 mm minimum
    
    4.3 Isolation Voltage
    Visol = 5 kV AC (50/60 Hz, 1 min)
    
    Weight: 300 g
    Mounting Torque: 5 N·m
    """
    
    blocks = extract_relevant_text_blocks(test_text, page_num=3)
    print(f"Found {len(blocks)} blocks:")
    for b in blocks:
        print(f"  - {b['heading']}: {b['text'][:80]}...")
