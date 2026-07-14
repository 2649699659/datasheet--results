"""
Excel Output Writer v1

Generates final_comparison.xlsx from Final Selector v1 document-based output.

Sheets:
    1. Final Comparison - final_candidate fields with Value/Condition/Page per document
    2. Review Needed - review_needed fields with all candidates + Condition
    3. Blocked - blocked fields with danger reasons + Condition
    4. Source Evidence - source text for all non-missing selections + Condition

Step 7.5: Condition fidelity fix - preserve original key names and units from datasheet.
- Split key normalization: V GS → VGS, I D → ID, T C → TC, R G → RG
- Unit preservation: TC=25°C, ID=150A, VGS=18V, Load=50µH
- Specific keys before generic: VGS before V, ID before I, TC before T, RG(ext) before R
"""

import re
from typing import Any, Dict, List, Optional, Tuple

import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter


# =============================================================================
# Helper Functions - Condition Extraction (Step 7.5)
# =============================================================================

# ------------------------------------------------------------------
# Step 1: Text Normalization (before regex matching)
# ------------------------------------------------------------------

def _normalize_for_condition(text: str) -> str:
    """
    Normalize raw source text for condition extraction.
    
    Operations (in order):
    1. Replace degree variants → °C
    2. Replace micro sign → μ
    3. Fix split keys: V GS → VGS, V DS → VDS, I D → ID, T C → TC, R G → RG
    4. Normalize spaces around =
    5. Collapse multiple spaces
    
    Note: does NOT change numerical values.
    """
    if not text:
        return text

    t = text

    # 1. Degree character normalization
    for deg in ("\u00b0", "\u2070", "\u2103", "\u33f1", "\uf0b0", "\u33f2", "\u00b2"):
        t = t.replace(deg, "\u00b0")
    # Handle ℃ (U+2103), ˚C (U+02DA + C), etc.
    t = re.sub(r"([\u2103\u3303])\s*C", "\u00b0C", t)
    t = re.sub(r"([\u00b0])\s*C", "\u00b0C", t)
    t = re.sub(r"([\u2070])\s*C", "\u00b0C", t)
    # Replace any remaining ˚ (U+02DA) with °
    t = t.replace("\u02da", "\u00b0")
    t = t.replace("\u00bf", "")  # Remove ¿ rogue char

    # 2. Micro sign normalization
    t = t.replace("\u00b5", "\u03bc")  # micro sign → greek mu

    # 3. Split key normalization (datasheet PDF extraction artifact)
    # These join single-letter subscripts that get split during PDF text extraction
    split_fixes = [
        (r"\bV\s+G\s+S\b", "VGS"),
        (r"\bV\s+D\s+S\b", "VDS"),
        (r"\bV\s+D\s+D\b", "VDD"),
        (r"\bV\s+R\b", "VR"),
        (r"\bV\s+A\s+C\b", "VAC"),
        (r"\bV\s+F\b", "VF"),
        (r"\bI\s+D\b", "ID"),
        (r"\bI\s+F\b", "IF"),
        (r"\bI\s+S\b", "IS"),
        (r"\bI\s+G\s+S\s+S\b", "IGSS"),
        (r"\bI\s+D\s+S\s+S\b", "IDSS"),
        (r"\bI\s+R\s+M\b", "IRM"),
        (r"\bI\s+R\s+R\s+M\b", "IRRM"),
        (r"\bT\s+C\b", "TC"),
        (r"\bT\s+J\b", "TJ"),
        # R G(ext) → RG(ext): R G (ext) → RG(ext)
        (r"\bR\s+G\s*\(\s*ext\s*\)\s*\(", "RG(ext)("),
        (r"\bR\s+G\b", "RG"),
        # Load: L OA D → Load
        (r"\bL\s+O\s+A\s+D\b", "Load"),
        (r"\bL\s+O\s+A\s+D(?:\s*\(\s*ext\s*\))", "Load"),
    ]
    for pattern, replacement in split_fixes:
        t = re.sub(pattern, replacement, t, flags=re.IGNORECASE)

    # 4. Normalize spaces around = (key=value without extra spaces)
    # "V =18V" → "V=18V", "VGS =18V" → "VGS=18V"
    t = re.sub(r"(\w)\s*=\s*", r"\1=", t)

    # 5. Collapse multiple spaces
    t = re.sub(r" {2,}", " ", t)
    t = t.strip()

    return t


# ------------------------------------------------------------------
# Step 2: Key Extraction Patterns (ordered by specificity)
# ------------------------------------------------------------------

# Each pattern: (key_name, compiled_regex, unit_suffix)
# - key_name: canonical display name (e.g., "VGS", "ID", "TC")
# - compiled_regex: MUST have ONE capture group = the numeric value
# - unit_suffix: string to append after the captured value (e.g., "V", "A", "°C", "Ω", "µH")
#
# IMPORTANT: The character class for numeric values must include "+" for signed values like "-5/+18"
# Pattern: [-\d./+]+ NOT [-\d./]+
#
# The unit-matching part (\s*V or \s*A) uses \s* (zero or more spaces) before the unit letter
# to handle both "value V" (with space) and "valueV" (without space).
#
# Word boundary \b is used at the start of key names to prevent partial matches.
# Negative lookahead (?![A-Za-z]) after the unit prevents matching when unit is followed by letters.

class _CondPattern:
    __slots__ = ('key', 'pattern', 'unit')
    def __init__(self, key: str, pattern: str, unit: str = ""):
        self.key = key
        self.pattern = re.compile(pattern, re.IGNORECASE)
        self.unit = unit


# Ordered by specificity: specific keys before generic keys.
# Generic keys (V, I, T, R, L) are only used when no specific key matched.
_COND_PATTERNS: List[_CondPattern] = [
    # ---- Voltage keys ---- (specific first, then general V)
    # Note: value char class [-\d./+]+ includes "+" for signed values like "-5/+18"
    _CondPattern("VGS",    r"\bVGS\s*=\s*([-\d./+]+)\s*V\b(?![A-Za-z])",               "V"),
    _CondPattern("VDS",    r"\bVDS\s*=\s*([-\d./+]+)\s*V\b(?![A-Za-z])",               "V"),
    _CondPattern("VDD",    r"\bVDD\s*=\s*([-\d./+]+)\s*V\b(?![A-Za-z])",               "V"),
    _CondPattern("VR",     r"\bVR\s*=\s*([-\d./+]+)\s*V\b(?![A-Za-z])",                 "V"),
    _CondPattern("VAC",    r"\bVAC\s*=\s*([-\d./+]+)\s*V\b(?![A-Za-z])",                "V"),
    _CondPattern("VF",     r"\bVF\s*=\s*([-\d./+]+)\s*V\b(?![A-Za-z])",                 "V"),
    _CondPattern("Visol",  r"\bVisol\s*=\s*([-\d./+]+)\s*V\b(?![A-Za-z])",             "V"),
    _CondPattern("BVDS",   r"\bBVDS\s*=\s*([-\d./+]+)\s*V\b(?![A-Za-z])",              "V"),
    # General V: only matches standalone V=numberV (not VGS=, VDS=, etc.)
    # Word boundary \b prevents V in VGS/VDS from matching
    _CondPattern("V",      r"\bV\s*=\s*([-\d./+]+)\s*V\b(?![A-Za-z])",                   "V"),

    # ---- Current keys ---- (specific first, then general I)
    _CondPattern("ID",     r"\bID\s*=\s*([-\d.]+)\s*(?:mA|A)\b",                      "A"),
    _CondPattern("IF",     r"\bIF\s*=\s*([-\d.]+)\s*(?:mA|A)\b",                      "A"),
    _CondPattern("IRM",    r"\bIRM\s*=\s*([-\d.]+)\s*(?:mA|A)\b",                     "A"),
    _CondPattern("IRRM",   r"\bIRRM\s*=\s*([-\d.]+)\s*(?:mA|A)\b",                    "A"),
    _CondPattern("IS",     r"\bIS\s*=\s*([-\d.]+)\s*(?:mA|A)\b",                      "A"),
    _CondPattern("IGSS",   r"\bIGSS\s*=\s*([-\d.]+)\s*(?:mA|A)\b",                    "A"),
    _CondPattern("IDSS",   r"\bIDSS\s*=\s*([-\d.]+)\s*(?:mA|A)\b",                    "A"),
    # General I: word boundary prevents I in ID/IF/IS from matching
    _CondPattern("I",       r"\bI\s*=\s*([-\d.]+)\s*(?:mA|A)\b",                        "A"),

    # ---- Temperature keys ----
    _CondPattern("TC",     r"\bTC\s*=\s*([-\d.]+)\s*(?:\u00b0C|°C|C)\b",              "°C"),
    _CondPattern("TJ",     r"\bTJ\s*=\s*([-\d.]+)\s*(?:\u00b0C|°C|C)\b",              "°C"),
    _CondPattern("Top",    r"\bTop\s*=\s*([-\d.]+)\s*(?:\u00b0C|°C|C)\b",            "°C"),
    _CondPattern("Tstg",   r"\bTstg\s*=\s*([-\d.]+)\s*(?:\u00b0C|°C|C)\b",          "°C"),
    _CondPattern("T",      r"\bT\s*=\s*([-\d.]+)\s*(?:\u00b0C|°C|C)\b",                "°C"),

    # ---- Resistance keys ----
    _CondPattern("RG(ext)", r"RG\s*\(\s*ext\s*\)\s*=\s*([-\d.]+)\s*(?:\u03a9|ohm)\b",  "Ω"),
    _CondPattern("RG",     r"\bRG\s*=\s*([-\d.]+)\s*(?:\u03a9|ohm)\b",                "Ω"),
    _CondPattern("R",       r"\bR\s*=\s*([-\d.]+)\s*(?:\u03a9|ohm)\b",                  "Ω"),

    # ---- Frequency ----
    _CondPattern("f",      r"\bf\s*=\s*([-\d.]+)\s*(?:MHz|kHz|Hz)\b",                  "Hz"),

    # ---- Load inductance ----
    _CondPattern("Load",   r"\bLoad\s*=\s*([-\d.]+)\s*(?:\u03bcH|µH)\b",             "µH"),
]


# ------------------------------------------------------------------
# Step 3: Static keywords (no numeric value)
# ------------------------------------------------------------------
_STATIC_KEYWORDS = frozenset([
    "Terminal to Terminal",
    "Terminal to Baseplate",
    "VDS=VGS",
])


# ------------------------------------------------------------------
# Step 4: Generic key suppression map
# When a specific key is found, suppress the generic counterpart.
# ------------------------------------------------------------------
_GENERIC_KEY_SUPPRESSES: Dict[str, str] = {
    # Voltage
    "VGS": "V", "VDS": "V", "VDD": "V", "VR": "V", "VAC": "V", "VF": "V", "Visol": "V", "BVDS": "V",
    # Current
    "ID": "I", "IF": "I", "IRM": "I", "IRRM": "I", "IS": "I", "IGSS": "I", "IDSS": "I",
    # Temperature
    "TC": "T", "TJ": "T", "Top": "T", "Tstg": "T",
    # Resistance
    "RG(ext)": "R", "RG": "R",
}


# ------------------------------------------------------------------
# Step 5: Extract condition from normalized text
# ------------------------------------------------------------------

def _extract_condition_from_text(src: str) -> str:
    """
    Extract condition key=value pairs from raw source text.
    
    Returns a "; "-joined string of conditions, e.g.:
    "VGS=18V; ID=150A; TC=25°C"
    
    Features:
    - Specific keys before generic: VGS before V, ID before I
    - Units preserved: °C, A, V, Ω, µH, Hz
    - Generic key suppression: if VGS found, don't add V
    - Split key normalization: V GS → VGS, I D → ID
    - Source text order preserved (first match wins per key)
    """
    if not src or len(src) > 2000:
        return ""

    normalized = _normalize_for_condition(src)

    parts: List[str] = []
    seen: set = set()
    suppressed_generics: set = set()

    # --- Static keywords (check in normalized text) ---
    norm_lower = normalized.lower()
    for kw in ("Terminal to Terminal", "Terminal to Baseplate"):
        if kw.lower() in norm_lower:
            parts.append(kw)
            seen.add(kw.lower())

    # --- VDS=VGS special case ---
    # Matches "V =V ;" or "V=V ;" in source. When present, suppress generic V at the same position.
    vds_vgs_pos = -1  # default: no VDS=VGS found
    vds_vgs_match = re.search(r"\bV\s*=\s*V\s*;", norm_lower, re.IGNORECASE)
    if vds_vgs_match:
        parts.append("VDS=VGS")
        seen.add("vds=vgs")
        suppressed_generics.add("V")  # suppress generic V pattern
        vds_vgs_pos = vds_vgs_match.start()  # remember position to skip

    # --- Dynamic patterns (ordered by specificity) ---
    for cp in _COND_PATTERNS:
        key_lower = cp.key.lower()

        # Skip if this key or its generic was already found
        if key_lower in seen:
            continue
        if cp.key in suppressed_generics:
            continue

        m = cp.pattern.search(normalized)
        if not m:
            continue

        # Skip generic V if match is at VDS=VGS position (we already captured VDS=VGS)
        if (cp.key == "V" and 'vds=vgs' in seen and
                hasattr(m, 'start') and m.start() == vds_vgs_pos):
            continue

        val = m.group(1)
        # Build snippet: key=value with unit
        snippet = f"{cp.key}={val}{cp.unit}"

        if key_lower not in seen:
            parts.append(snippet)
            seen.add(key_lower)

        # Suppress generic counterpart
        if cp.key in _GENERIC_KEY_SUPPRESSES:
            suppressed_generics.add(_GENERIC_KEY_SUPPRESSES[cp.key])

    # ---- Post-processing: upgrade generic V → VGS if GS subscript appears in text ----
    # When "GS" appears as a standalone token in the source and generic V was extracted,
    # upgrade to VGS (most likely the intended key in datasheet context)
    parts_lower = {p.lower() for p in parts}
    if ("vgs" not in parts_lower and
            any(p.lower().startswith("v=") for p in parts) and
            re.search(r"\bGS\b", normalized)):
        # Replace the first generic "V=..." with "VGS=..."
        new_parts = []
        upgraded = False
        for p in parts:
            if not upgraded and p.lower().startswith("v=") and "vgs" not in p.lower():
                # Upgrade: replace value with same value but key=VGS
                # Extract value from "V=VALUEUNIT"
                mv = re.match(r"(V=)([\d./+-]+)(.*)", p)
                if mv:
                    new_parts.append(f"VGS={mv.group(2)}{mv.group(3)}")
                    upgraded = True
                    continue
            new_parts.append(p)
        parts = new_parts

    result = "; ".join(parts[:8])
    return result


# ------------------------------------------------------------------
# Step 6: Format condition from param dict
# ------------------------------------------------------------------

_GENERIC_KEYS_IN_CONDITION = frozenset(["V=", "I=", "T=", "R=", "L="])


def format_condition(param: Optional[Dict[str, Any]]) -> str:
    """
    Format condition string from param dict.

    Priority:
        1. If param["condition"] contains generic keys (V=, I=, T=, R=)
           AND source_text is available, re-extract from source_text for better fidelity.
        2. param["condition"] (normalized)
        3. param["condition_values"] (list joined with "; ")
        4. Extract from param["source_text"]

    Returns normalized condition string.
    """
    if not param:
        return ""

    # Priority 1: check if existing condition is generic and source_text available
    cond = param.get("condition") or ""
    src = param.get("source_text") or ""

    if cond.strip() and src.strip():
        # Check if condition contains generic keys
        cond_lower = cond.lower()
        has_generic = any(gk in cond_lower for gk in _GENERIC_KEYS_IN_CONDITION)
        if has_generic:
            extracted = _extract_condition_from_text(src)
            if extracted:
                return extracted

    # Priority 2: use existing condition (normalized)
    if cond.strip():
        return _normalize_for_condition(cond.strip())

    # Priority 3: condition_values list
    cv = param.get("condition_values") or []
    if cv and any(str(v).strip() for v in cv):
        parts = []
        for v in cv:
            s = str(v).strip()
            if s:
                parts.append(s)
        if parts:
            return "; ".join(parts)

    # Priority 4: extract from source_text
    if src.strip():
        return _extract_condition_from_text(src)

    return ""


# =============================================================================
# Other Helper Functions (unchanged from v1)
# =============================================================================

def get_param_unit(param: Optional[Dict[str, Any]]) -> str:
    """Get unit from param dict, in priority order."""
    if not param:
        return ""
    return param.get("original_unit") or param.get("normalized_unit") or param.get("unit") or ""
def format_param_value(param: Optional[Dict[str, Any]]) -> str:
    """Format parameter value as string per spec rules."""
    if not param:
        return ""

    val = param.get("value")
    min_val = param.get("min")
    typ = param.get("typ")
    max_val = param.get("max")

    parts = []
    if min_val is not None:
        parts.append(f"min={min_val}")
    if typ is not None:
        parts.append(f"typ={typ}")
    if max_val is not None:
        parts.append(f"max={max_val}")

    if not parts:
        if val is not None:
            return str(val)
        return ""

    # Format based on which values exist
    if min_val is not None and max_val is not None and typ is None:
        return f"{min_val} ~ {max_val}"
    if typ is not None and max_val is not None and min_val is None:
        return f"typ={typ}; max={max_val}"
    if len(parts) >= 2:
        return "; ".join(parts)
    return parts[0] if parts else (str(val) if val is not None else "")


def get_document_display_name(doc: Dict[str, Any]) -> str:
    """Get display name for a document."""
    pdf_stem = doc.get("pdf_stem") or ""
    file_name = doc.get("file_name") or ""
    if pdf_stem:
        return pdf_stem
    if file_name:
        return file_name
    return "unknown"


def _shorten_source_text(text: str, max_len: int = 300) -> str:
    """Shorten source text to max_len, preserve start."""
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


# =============================================================================
# Column Definitions (v1: Value / Condition / Page per document)
# =============================================================================

# Final Comparison: Parameter | Unit | [DocName Value] | [DocName Condition] | [DocName Page] | Notes
# Review Needed: Document | Field ID | Label | Candidate Type | Value | Unit | Condition | Score | Reason | Warnings | Page | Table | Row | Source Text
# Blocked: Document | Field ID | Label | Block Reason | Value | Unit | Condition | Page | Source Text
# Source Evidence: Document | Field ID | Selection Status | Value | Unit | Condition | Page | Table | Row | Source Hash | Source Text


# =============================================================================
# Sheet Writers
# =============================================================================

def _write_header_row(ws, cols: List[str], row: int = 1) -> None:
    """Write a bold header row."""
    for col_idx, col_name in enumerate(cols, start=1):
        cell = ws.cell(row=row, column=col_idx, value=col_name)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def _set_col_width(ws, col_idx: int, width: float) -> None:
    col_letter = get_column_letter(col_idx)
    ws.column_dimensions[col_letter].width = width


def _write_final_comparison(ws, selection_result: Dict[str, Any]) -> None:
    """
    Write Final Comparison sheet (Sheet 1).

    Per-document columns: Value | Condition | Page
    Column layout: Parameter | Unit | [Doc1 Value] | [Doc1 Condition] | [Doc1 Page] | ... | Notes
    """
    docs = selection_result.get("documents", [])

    # Build column headers
    # Per document: Value | Condition | Page (3 cols each)
    doc_cols: List[Tuple[str, int]] = []  # (doc_name, start_col)
    header = ["Parameter", "Unit"]
    for doc in docs:
        doc_name = get_document_display_name(doc)
        start_col = len(header) + 1
        doc_cols.append((doc_name, start_col))
        header.extend([f"{doc_name} Value", f"{doc_name} Condition", f"{doc_name} Page"])

    _write_header_row(ws, header, row=1)
    ws.freeze_panes = "C2"

    # Build doc_field_map
    doc_field_map = []
    for doc in docs:
        field_map = {}
        for f in doc.get("fields", []):
            field_map[f["field_id"]] = f
        doc_field_map.append(field_map)

    # Ordered fields (final_candidate only)
    all_final_ids = set()
    for dmap in doc_field_map:
        for fid, f in dmap.items():
            if f.get("selection_status") == "final_candidate":
                all_final_ids.add(fid)

    if docs and docs[0].get("fields"):
        ordered_fields = [f["field_id"] for f in docs[0]["fields"] if f["field_id"] in all_final_ids]
    else:
        ordered_fields = sorted(all_final_ids)

    row = 2
    for fid in ordered_fields:
        # Get label
        label = fid
        for dmap in doc_field_map:
            if fid in dmap:
                label = dmap[fid].get("label") or fid
                break
        ws.cell(row=row, column=1, value=label)
        ws.cell(row=row, column=1).font = Font(bold=True)

        # Get unit from first doc
        unit = ""
        for dmap in doc_field_map:
            if fid in dmap:
                p = dmap[fid].get("selected_param")
                if p:
                    unit = get_param_unit(p)
                    break
        ws.cell(row=row, column=2, value=unit)

        # Per-document columns
        for doc_idx, (doc_name, start_col) in enumerate(doc_cols):
            dmap = doc_field_map[doc_idx]
            if fid not in dmap:
                continue
            f = dmap[fid]
            if f.get("selection_status") != "final_candidate":
                continue
            p = f.get("selected_param")

            value_col = start_col
            cond_col = start_col + 1
            page_col = start_col + 2

            # Value
            value_str = format_param_value(p)
            ws.cell(row=row, column=value_col, value=value_str)

            # Condition
            cond_str = format_condition(p)
            ws.cell(row=row, column=cond_col, value=cond_str)
            ws.cell(row=row, column=cond_col).alignment = Alignment(wrap_text=True)

            # Page
            page_val = str(p.get("source_page", "")) if p else ""
            ws.cell(row=row, column=page_col, value=page_val)

        row += 1

    # Column widths
    _set_col_width(ws, 1, 22)  # Parameter
    _set_col_width(ws, 2, 8)   # Unit
    for doc_name, start_col in doc_cols:
        _set_col_width(ws, start_col, 22)     # Value
        _set_col_width(ws, start_col + 1, 30) # Condition
        _set_col_width(ws, start_col + 2, 8)  # Page


def _write_review_needed(ws, selection_result: Dict[str, Any]) -> None:
    """
    Write Review Needed sheet (Sheet 2).

    Columns: Document | Field ID | Label | Candidate Type | Value | Unit | Condition | Score | Reason | Warnings | Page | Table | Row | Source Text
    """
    cols = [
        "Document", "Field ID", "Label", "Candidate Type",
        "Value", "Unit", "Condition",
        "Score", "Reason", "Warnings",
        "Page", "Table", "Row", "Source Text",
    ]
    _write_header_row(ws, cols, row=1)
    ws.freeze_panes = "A2"

    row = 2
    for doc in selection_result.get("documents", []):
        doc_name = get_document_display_name(doc)
        for f in doc.get("fields", []):
            if f.get("selection_status") != "review_needed":
                continue

            fid = f["field_id"]
            label = f.get("label") or fid
            score = f.get("selector_score", 0)
            reason = f.get("selector_reason", "")
            warnings = "; ".join(f.get("selector_warnings", [])[:3])

            # Primary selected candidate
            p = f.get("selected_param")
            value_str = format_param_value(p)
            unit = get_param_unit(p)
            cond_str = format_condition(p)
            page = p.get("source_page", "") if p else ""
            table_idx = p.get("table_index", "") if p else ""
            row_idx = p.get("row_index", "") if p else ""
            source_text = _shorten_source_text(p.get("source_text", "") if p else "")

            ws.cell(row=row, column=1, value=doc_name)
            ws.cell(row=row, column=2, value=fid)
            ws.cell(row=row, column=3, value=label)
            ws.cell(row=row, column=4, value="selected")
            ws.cell(row=row, column=5, value=value_str)
            ws.cell(row=row, column=6, value=unit)
            ws.cell(row=row, column=7, value=cond_str)
            ws.cell(row=row, column=7).alignment = Alignment(wrap_text=True)
            ws.cell(row=row, column=8, value=score)
            ws.cell(row=row, column=9, value=reason[:300])
            ws.cell(row=row, column=10, value=warnings[:100])
            ws.cell(row=row, column=11, value=str(page) if page else "")
            ws.cell(row=row, column=12, value=str(table_idx) if table_idx != "" else "")
            ws.cell(row=row, column=13, value=str(row_idx) if row_idx != "" else "")
            ws.cell(row=row, column=14, value=source_text)
            ws.cell(row=row, column=14).alignment = Alignment(wrap_text=True)
            row += 1

            # Alternative candidates
            for alt in f.get("review_params", []):
                alt_value_str = format_param_value(alt)
                alt_unit = get_param_unit(alt)
                alt_cond_str = format_condition(alt)
                alt_page = alt.get("source_page", "")
                alt_table = alt.get("table_index", "")
                alt_row = alt.get("row_index", "")
                alt_text = _shorten_source_text(alt.get("source_text", ""))
                alt_reason = alt.get("review_reason", "")

                ws.cell(row=row, column=1, value=doc_name)
                ws.cell(row=row, column=2, value=fid)
                ws.cell(row=row, column=3, value=label)
                ws.cell(row=row, column=4, value="alternative_review")
                ws.cell(row=row, column=5, value=alt_value_str)
                ws.cell(row=row, column=6, value=alt_unit)
                ws.cell(row=row, column=7, value=alt_cond_str)
                ws.cell(row=row, column=7).alignment = Alignment(wrap_text=True)
                ws.cell(row=row, column=8, value="")
                ws.cell(row=row, column=9, value=alt_reason[:300])
                ws.cell(row=row, column=10, value="")
                ws.cell(row=row, column=11, value=str(alt_page) if alt_page else "")
                ws.cell(row=row, column=12, value=str(alt_table) if alt_table != "" else "")
                ws.cell(row=row, column=13, value=str(alt_row) if alt_row != "" else "")
                ws.cell(row=row, column=14, value=alt_text)
                ws.cell(row=row, column=14).alignment = Alignment(wrap_text=True)
                row += 1

    # Column widths
    _set_col_width(ws, 1, 20)   # Document
    _set_col_width(ws, 2, 18)   # Field ID
    _set_col_width(ws, 3, 20)   # Label
    _set_col_width(ws, 4, 18)   # Candidate Type
    _set_col_width(ws, 5, 20)   # Value
    _set_col_width(ws, 6, 8)    # Unit
    _set_col_width(ws, 7, 35)   # Condition
    _set_col_width(ws, 8, 8)    # Score
    _set_col_width(ws, 9, 40)   # Reason
    _set_col_width(ws, 10, 30)  # Warnings
    _set_col_width(ws, 11, 6)   # Page
    _set_col_width(ws, 12, 6)   # Table
    _set_col_width(ws, 13, 6)    # Row
    _set_col_width(ws, 14, 60)  # Source Text


def _write_blocked(ws, selection_result: Dict[str, Any]) -> None:
    """
    Write Blocked sheet (Sheet 3).

    Columns: Document | Field ID | Label | Block Reason | Value | Unit | Condition | Page | Source Text
    """
    cols = [
        "Document", "Field ID", "Label", "Block Reason",
        "Value", "Unit", "Condition", "Page", "Source Text",
    ]
    _write_header_row(ws, cols, row=1)
    ws.freeze_panes = "A2"

    row = 2
    for doc in selection_result.get("documents", []):
        doc_name = get_document_display_name(doc)
        for f in doc.get("fields", []):
            if f.get("selection_status") != "blocked":
                continue

            fid = f["field_id"]
            label = f.get("label") or fid
            reason = f.get("selector_reason", "")
            p = f.get("selected_param")
            value_str = format_param_value(p)
            unit = get_param_unit(p)
            cond_str = format_condition(p)
            page = p.get("source_page", "") if p else ""
            source_text = _shorten_source_text(p.get("source_text", "") if p else "")

            ws.cell(row=row, column=1, value=doc_name)
            ws.cell(row=row, column=2, value=fid)
            ws.cell(row=row, column=3, value=label)
            ws.cell(row=row, column=4, value=reason[:300])
            ws.cell(row=row, column=5, value=value_str)
            ws.cell(row=row, column=6, value=unit)
            ws.cell(row=row, column=7, value=cond_str)
            ws.cell(row=row, column=7).alignment = Alignment(wrap_text=True)
            ws.cell(row=row, column=8, value=str(page) if page else "")
            ws.cell(row=row, column=9, value=source_text)
            ws.cell(row=row, column=9).alignment = Alignment(wrap_text=True)
            row += 1

    # Column widths
    _set_col_width(ws, 1, 20)  # Document
    _set_col_width(ws, 2, 18)  # Field ID
    _set_col_width(ws, 3, 20)  # Label
    _set_col_width(ws, 4, 45)  # Block Reason
    _set_col_width(ws, 5, 20)  # Value
    _set_col_width(ws, 6, 8)   # Unit
    _set_col_width(ws, 7, 35)  # Condition
    _set_col_width(ws, 8, 6)   # Page
    _set_col_width(ws, 9, 60)  # Source Text


def _write_source_evidence(ws, selection_result: Dict[str, Any]) -> None:
    """
    Write Source Evidence sheet (Sheet 4).

    Columns: Document | Field ID | Selection Status | Value | Unit | Condition | Page | Table | Row | Source Hash | Source Text
    """
    cols = [
        "Document", "Field ID", "Selection Status",
        "Value", "Unit", "Condition",
        "Page", "Table", "Row", "Source Hash", "Source Text",
    ]
    _write_header_row(ws, cols, row=1)
    ws.freeze_panes = "A2"

    row = 2
    for doc in selection_result.get("documents", []):
        doc_name = get_document_display_name(doc)
        doc_id = doc.get("document_id", "")
        for f in doc.get("fields", []):
            status = f.get("selection_status", "")
            if status == "missing":
                continue

            fid = f["field_id"]
            label = f.get("label") or fid
            p = f.get("selected_param")
            value_str = format_param_value(p)
            unit = get_param_unit(p)
            cond_str = format_condition(p)
            page = p.get("source_page", "") if p else ""
            table_idx = p.get("table_index", "") if p else ""
            row_idx = p.get("row_index", "") if p else ""
            source_hash = p.get("source_hash", "") if p else ""
            source_text = p.get("source_text", "")[:500] if p else ""

            ws.cell(row=row, column=1, value=doc_name)
            ws.cell(row=row, column=2, value=fid)
            ws.cell(row=row, column=3, value=label)
            ws.cell(row=row, column=4, value=status)
            ws.cell(row=row, column=5, value=value_str)
            ws.cell(row=row, column=6, value=unit)
            ws.cell(row=row, column=7, value=cond_str)
            ws.cell(row=row, column=7).alignment = Alignment(wrap_text=True)
            ws.cell(row=row, column=8, value=str(page) if page else "")
            ws.cell(row=row, column=9, value=str(table_idx) if table_idx != "" else "")
            ws.cell(row=row, column=10, value=str(row_idx) if row_idx != "" else "")
            ws.cell(row=row, column=11, value=source_hash)
            ws.cell(row=row, column=12, value=source_text)
            ws.cell(row=row, column=12).alignment = Alignment(wrap_text=True)
            row += 1

    # Column widths
    _set_col_width(ws, 1, 18)  # Document
    _set_col_width(ws, 2, 18)  # Field ID
    _set_col_width(ws, 3, 18)  # Label
    _set_col_width(ws, 4, 18)  # Selection Status
    _set_col_width(ws, 5, 20)  # Value
    _set_col_width(ws, 6, 8)   # Unit
    _set_col_width(ws, 7, 35)  # Condition
    _set_col_width(ws, 8, 6)   # Page
    _set_col_width(ws, 9, 6)   # Table
    _set_col_width(ws, 10, 6)  # Row
    _set_col_width(ws, 11, 16) # Source Hash
    _set_col_width(ws, 12, 70) # Source Text


# =============================================================================
# Main Entry Point
# =============================================================================

def write_excel_report(selection_result: Dict[str, Any], output_path: str) -> None:
    """
    Write Excel report from Final Selector v1 document-based selection result.

    Args:
        selection_result: Document-based selection result from select_final_candidates()
        output_path: Path to output xlsx file
    """
    wb = openpyxl.Workbook()

    default_sheet = wb.active
    wb.remove(default_sheet)

    ws1 = wb.create_sheet("Final Comparison")
    ws2 = wb.create_sheet("Review Needed")
    ws3 = wb.create_sheet("Blocked")
    ws4 = wb.create_sheet("Source Evidence")

    _write_final_comparison(ws1, selection_result)
    _write_review_needed(ws2, selection_result)
    _write_blocked(ws3, selection_result)
    _write_source_evidence(ws4, selection_result)

    wb.save(output_path)
