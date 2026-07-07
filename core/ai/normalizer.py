"""
Generic AI Normalizer for fixing field misalignment in AI extraction output.

This is MANUFACTURER-AGNOSTIC. Only general-purpose normalization rules.
No vendor-specific part numbers or values.
"""

import re
from typing import Optional


# ---------------------------------------------------------------------------
# Legal unit whitelist
# ---------------------------------------------------------------------------
UNIT_WHITELIST = {
    # Thermal
    "°C/W", "°C/W",
    # Voltage
    "kV", "mV", "μV", "uV",
    # Current
    "kA", "mA", "μA", "uA", "nA",
    # Resistance
    "kΩ", "MΩ", "mΩ",
    # Capacitance
    "nF", "pF", "μF", "uF", "mF",
    # Charge
    "nC", "pC",
    # Energy
    "mJ", "μJ", "uJ",
    # Power
    "kW", "mW",
    # Frequency
    "kHz", "MHz", "GHz",
    # Time
    "ms", "μs", "us", "ns",
    # Inductance
    "nH", "μH", "uH", "mH",
    # Conductance
    "mS", "μS",
    # Torque
    "N-m",
    # Length
    "mm", "μm", "um", "nm", "cm",
    # Weight
    "g", "kg",
    # Temperature
    "°C",
    # Base units (only matched when adjacent to number)
    "V", "A", "Ω", "F", "H", "W", "J", "S", "Hz",
}

# Units that are single-character (must be adjacent to number)
_SINGLE_CHAR_UNITS = {"V", "A", "Ω", "F", "H", "W", "J", "S", "Hz", "g", "S"}

# Build sorted patterns (longest first to avoid partial matches)
_UNIT_PATTERNS = sorted(UNIT_WHITELIST, key=len, reverse=True)
_UNIT_RE = re.compile(
    "(" + "|".join(re.escape(u) for u in _UNIT_PATTERNS) + ")",
    0,  # not case-insensitive by default
)


def _is_legal_unit(s: str) -> bool:
    """Check if a unit string is in the whitelist."""
    if not s:
        return False
    s = s.strip()
    # Normalize unicode
    s = s.replace("µ", "μ").replace("μ", "μ")
    return s in UNIT_WHITELIST


# ---------------------------------------------------------------------------
# Symbol aliases
# ---------------------------------------------------------------------------
SYMBOL_ALIASES = {
    # Thermal
    "rthjc": "Rth JC", "rth jc": "Rth JC", "rth(j-c)": "Rth JC",
    "rth_jc": "Rth JC", "rth(jc)": "Rth JC",
    # Capacitance
    "ciss": "Ciss", "input capacitance": "Ciss",
    "coss": "Coss", "output capacitance": "Coss",
    "crss": "Crss", "reverse transfer capacitance": "Crss",
    # Gate charge
    "qg": "QG", "qg total": "QG", "total gate charge": "QG",
    "qgs": "QGS", "qgd": "QGD",
    # Reverse recovery
    "qrr": "QRR", "reverse recovery charge": "QRR",
    "err": "Err", "erec": "Err", "reverse recovery energy": "Err",
    "eon": "Eon", "eoff": "Eoff",
    # Resistance
    "rds on": "RDS(on)", "rds(on)": "RDS(on)", "rds": "RDS(on)", "rdson": "RDS(on)",
    # Voltage symbols
    "vds": "VDS", "vgs": "VGS", "vgs(th)": "VGS(th)", "vgs(th)": "VGS(th)",
    "vgs(max)": "VGS(max)", "vgs_max": "VGS(max)",
    "v(br)dss": "V(BR)DSS", "vbrdss": "V(BR)DSS", "v(br)": "V(BR)DSS",
    # Isolation
    "visol": "Visol", "viso": "Visol", "isolation voltage": "Visol",
    "v isolation": "Visol",
    # Gate resistance
    "rg int": "RG(int)", "rg(int)": "RG(int)", "rg_internal": "RG(int)",
    "internal gate resistance": "RG(int)", "gate resistance internal": "RG(int)",
    # Inductance
    "lstray": "Lstray", "stray inductance": "Lstray", "l stray": "Lstray",
    # Diode
    "trr": "trr", "reverse recovery time": "trr",
    "irms": "IRRM",
    # Transconductance
    "gfs": "gfs",
}


def canonicalize_symbol(raw: str) -> str:
    if not raw:
        return raw
    key = str(raw).strip().lower()
    return SYMBOL_ALIASES.get(key, str(raw).strip())


# ---------------------------------------------------------------------------
# Mechanical / insulation parameter inference rules
# ---------------------------------------------------------------------------
_MECHANICAL_INFER = [
    # (trigger_lower, symbol, parameter)
    ("clearance distance", "Clearance", "Clearance Distance"),
    ("clearance", "Clearance", "Clearance"),
    ("creepage distance", "Creepage", "Creepage Distance"),
    ("creepage", "Creepage", "Creepage"),
    ("isolation voltage", "Visol", "Isolation Voltage"),
    ("isolation", "Visol", "Isolation Voltage"),
    ("visol", "Visol", "Visol"),
    ("viso", "Visol", "Visol"),
    ("weight", "Weight", "Weight"),
    ("mounting torque", "Mounting Torque", "Mounting Torque"),
    ("stray inductance", "Lstray", "Stray Inductance"),
]


def _infer_mechanical_symbol(source_text: str, parameter: str, section: str) -> Optional[tuple]:
    """Infer symbol/parameter from source text for mechanical params."""
    combined = f"{source_text} {parameter} {section}".lower()
    for trigger, sym, param in _MECHANICAL_INFER:
        if trigger in combined:
            return (sym, param)
    return None


# ---------------------------------------------------------------------------
# Priority 2: Pipe-format table parsing
# ---------------------------------------------------------------------------
def parse_pipe_source_text(source_text: str) -> Optional[dict]:
    """
    Parse a pipe-delimited source_text into structured fields.
    
    Returns dict with keys: symbol, min, typ, max, unit, condition
    or None if not a pipe-format row.
    """
    if "|" not in source_text:
        return None
    
    # Split by pipe, trim whitespace from each cell
    cells = [c.strip() for c in source_text.split("|")]
    
    if len(cells) < 2:
        return None
    
    result = {"symbol": None, "min": None, "typ": None, "max": None, 
              "unit": None, "condition": None}
    
    # Classify each cell
    value_cells = []
    unit_candidates = []
    condition_cells = []
    symbol_candidates = []
    
    known_symbols_lower = {
        "ciss", "coss", "crss", "qg", "qgs", "qgd", "qrr", "trr",
        "eon", "eoff", "err", "vf", "vds", "vgs", "vgs(th)",
        "v(br)dss", "rds(on)", "rg(int)", "rth jc", "rthjc",
        "id", "idss", "igss", "idm", "if", "ir", "gfs",
        "e", "w", "tc", "tj", "tvj", "pd",
    }
    
    condition_keywords = {
        "vgs", "vds", "id", "vd", "vg", "tc", "tj", "tvj",
        "f=", "rg", "l=", "vac", "if=", "ir=", "vr=",
        "vgs=", "vds=", "di", "dt", "terminal", "baseplate",
        "v =", "i =", "t =",
    }
    
    for cell in cells:
        if not cell or cell in ("None", "none", "-", "—"):
            continue
        
        cell_lower = cell.lower()
        
        # Check if it's a known symbol
        if cell_lower in known_symbols_lower:
            symbol_candidates.append(cell)
            continue
        
        # Check if it contains a unit (exact match against whitelist)
        if _is_legal_unit(cell):
            unit_candidates.append(cell)
            continue
        
        # Check if it contains a condition keyword
        if any(kw in cell_lower for kw in condition_keywords):
            condition_cells.append(cell)
            continue
        
        # Check if it's a number
        num_match = re.match(r"^[<>]?=?[\d.\-/]+$", cell.strip())
        if num_match:
            value_cells.append(cell)
            continue
        
        # Check if it contains a number + unit combination
        num_unit = re.match(r"^([\d.\-/]+)\s*([A-Za-z°Ωμ]+)$", cell.strip())
        if num_unit:
            value_cells.append(num_unit.group(1))
            if _is_legal_unit(num_unit.group(2)):
                unit_candidates.append(num_unit.group(2))
            continue
    
    # Assign: first symbol candidate → symbol
    if symbol_candidates:
        result["symbol"] = symbol_candidates[0]
    
    # Assign: first unit candidate → unit
    if unit_candidates:
        result["unit"] = unit_candidates[0]
    
    # Assign: condition = join condition cells
    if condition_cells:
        result["condition"] = "; ".join(condition_cells)
    
    # Assign values to min/typ/max
    # Simple strategy: if 1 value → typ, if 2 → min/max, if 3 → min/typ/max
    if value_cells:
        if len(value_cells) == 1:
            result["typ"] = value_cells[0]
        elif len(value_cells) == 2:
            result["min"] = value_cells[0]
            result["max"] = value_cells[1]
        elif len(value_cells) >= 3:
            result["min"] = value_cells[0]
            result["typ"] = value_cells[1]
            result["max"] = value_cells[2]
    
    # Only return if we actually found something useful
    if any(v is not None for v in [result["symbol"], result["typ"], result["unit"]]):
        return result
    return None


# ---------------------------------------------------------------------------
# Priority 3: Number + unit pattern (with proper boundaries)
# ---------------------------------------------------------------------------
def extract_unit_from_text(source_text: str, near_value: str = None) -> Optional[str]:
    """
    Extract unit from source_text with proper boundaries.
    
    Priority:
    1. Look for multi-char units first (mΩ, nF, kV, etc.)
    2. Only match single-char units (V, A, Ω, etc.) when they appear
       AFTER a number (with optional space), not as part of a word.
    """
    if not source_text:
        return None
    
    # Strategy: find number+unit patterns with proper boundaries
    
    # Pattern: number followed by optional space then unit
    # Only match single-char units when preceded by a digit
    multi_char_units = [
        "°C/W", "mΩ", "kΩ", "MΩ", "mΩ", "kV", "mV", "μV", "uV",
        "kA", "mA", "μA", "uA", "nA",
        "nF", "pF", "μF", "uF", "mF",
        "nC", "pC", "μC", "uC",
        "mJ", "μJ", "uJ",
        "kW", "mW",
        "kHz", "MHz", "GHz",
        "ms", "μs", "us", "ns",
        "nH", "μH", "uH", "mH",
        "mS", "μS",
        "N-m",
        "mm", "μm", "um", "nm", "cm",
        "kg",
        "°C",
    ]
    
    # Build regex for multi-char units
    multi_re = "|".join(re.escape(u) for u in multi_char_units)
    if multi_re:
        m = re.search(multi_re, source_text, 0)  # case-sensitive
        if m:
            return m.group(0)
    
    # Single-char units: ONLY match when immediately after a digit
    # Must be preceded by a digit with optional whitespace
    single_char_units = {"V": "V", "A": "A", "Ω": "Ω", "F": "F", "H": "H",
                         "W": "W", "J": "J", "S": "S", "g": "g"}
    
    for unit_char, canonical in single_char_units.items():
        # Look for digit + optional space + unit_char as a distinct token
        # Use negative lookbehind to ensure not part of a longer word
        pattern = r"(?<![A-Za-z°Ωμ])" + re.escape(unit_char) + r"(?![A-Za-z°Ωμ])"
        if re.search(pattern, source_text):
            return canonical
    
    return None


# ---------------------------------------------------------------------------
# Main fix_missing_fields function
# ---------------------------------------------------------------------------
def fix_missing_fields(param: dict) -> tuple:
    """
    Fix missing unit, symbol, condition from source_text.
    Priority: preserve existing valid → pipe parse → number+unit pattern.
    Returns (fixed_param, list_of_notes).
    """
    p = dict(param)
    notes = []
    
    st = p.get("source_text") or ""
    
    # ---- Priority 1: Keep existing valid unit ----
    existing_unit = p.get("unit")
    unit_valid = existing_unit and str(existing_unit).strip() not in ("", "-", "—", "None", "null")
    if unit_valid:
        p["unit"] = str(existing_unit).strip()
        # Still try to fix symbol if missing
        pass  # fall through to symbol fix
    
    # ---- Priority 2: Pipe format parsing ----
    pipe_parsed = None
    if "|" in st:
        pipe_parsed = parse_pipe_source_text(st)
    
    if pipe_parsed:
        # Symbol from pipe
        if pipe_parsed.get("symbol") and (not p.get("symbol") or str(p.get("symbol")).strip() in ("", "-", "—", "None")):
            p["symbol"] = pipe_parsed["symbol"]
            notes.append("symbol_from_pipe")
        
        # Unit from pipe (only if we don't have a valid unit)
        if not unit_valid and pipe_parsed.get("unit"):
            pipe_unit = pipe_parsed["unit"]
            if _is_legal_unit(pipe_unit):
                p["unit"] = pipe_unit
                notes.append(f"unit_from_pipe:{pipe_unit}")
        
        # Value fields from pipe
        if pipe_parsed.get("typ") and not p.get("typ"):
            v = pipe_parsed["typ"]
            if str(v).strip() not in ("", "-", "—", "None"):
                p["typ"] = v
                notes.append("typ_from_pipe")
        
        if pipe_parsed.get("min") and not p.get("min"):
            v = pipe_parsed["min"]
            if str(v).strip() not in ("", "-", "—", "None"):
                p["min"] = v
                notes.append("min_from_pipe")
        
        if pipe_parsed.get("max") and not p.get("max"):
            v = pipe_parsed["max"]
            if str(v).strip() not in ("", "-", "—", "None"):
                p["max"] = v
                notes.append("max_from_pipe")
        
        if pipe_parsed.get("condition") and not p.get("condition"):
            c = pipe_parsed["condition"]
            if str(c).strip() not in ("", "-", "—", "None"):
                p["condition"] = c
                notes.append("condition_from_pipe")
    
    # ---- Priority 3: Number + unit extraction ----
    # Only if unit still missing
    if not p.get("unit") or str(p.get("unit")).strip() in ("", "-", "—", "None"):
        val = str(p.get("typ") or p.get("value") or p.get("min") or p.get("max") or "")
        
        # Try full source_text
        extracted_unit = extract_unit_from_text(st, val)
        if extracted_unit:
            p["unit"] = extracted_unit
            notes.append(f"unit_from_text:{extracted_unit}")
    
    # ---- Fix symbol if still missing ----
    sym = (p.get("symbol") or "").strip()
    if not sym or sym in ("", "-", "—", "None"):
        # Try mechanical parameter inference
        inferred = _infer_mechanical_symbol(
            st, p.get("parameter") or "", p.get("section") or ""
        )
        if inferred:
            new_sym, new_param = inferred
            p["symbol"] = new_sym
            if new_param and (not p.get("parameter") or p.get("parameter") in ("", "-", "—", "None")):
                p["parameter"] = new_param
            notes.append(f"symbol_inferred:{new_sym}")
    
    # ---- Infer condition from source_text if missing ----
    if not p.get("condition") or str(p.get("condition")).strip() in ("", "-", "—", "None"):
        cond = _extract_condition_from_text(st, p.get("symbol") or "")
        if cond:
            p["condition"] = cond
            notes.append("condition_inferred")
    
    # ---- Normalize symbol via alias ----
    if p.get("symbol"):
        old_sym = p["symbol"]
        new_sym = canonicalize_symbol(p["symbol"])
        if new_sym != old_sym:
            notes.append(f"symbol_alias:{old_sym}->{new_sym}")
            p["symbol"] = new_sym
    
    # ---- Fix: value → typ ----
    if not p.get("typ") or str(p.get("typ")).strip() in ("", "-", "—", "None"):
        if p.get("value") and str(p.get("value")).strip() not in ("", "-", "—", "None", "null"):
            p["typ"] = p["value"]
            p["value"] = None
            notes.append("value_to_typ")
    
    # ---- Fix: range in typ (e.g., "150/175") ----
    typ_val = str(p.get("typ") or "")
    if "/" in typ_val and not p.get("min") and not p.get("max"):
        parts = typ_val.split("/")
        if len(parts) == 2:
            try:
                float(parts[0].strip())
                float(parts[1].strip())
                p["min"] = parts[0].strip()
                p["max"] = parts[1].strip()
                p["typ"] = None
                notes.append("typ_range_split")
            except (ValueError, IndexError):
                pass
    
    # ---- Cleanup ----
    for key in ["parameter", "condition"]:
        if p.get(key):
            p[key] = str(p[key]).strip()
            p[key] = re.sub(r"^[\s|;:,:\-–—]+|[\s|;:,:\-–—]+$", "", p[key])
    
    return p, notes


def _extract_condition_from_text(source_text: str, symbol: str) -> Optional[str]:
    """Extract condition text from source_text."""
    if not source_text:
        return None
    
    # Look for common condition patterns
    cond_keywords = [
        "vgs=", "vds=", "id=", "vd=", "vg=", "if=", "ir=", "vr=",
        "tc=", "tj=", "tvj=", "f=", "rg=", "l=", "vac=",
        "di/dt", "di=", "dt=",
        "terminal", "baseplate",
    ]
    
    # Find text after the first condition keyword
    text_lower = source_text.lower()
    for kw in cond_keywords:
        idx = text_lower.find(kw)
        if idx >= 0:
            # Take text from keyword to end (up to 80 chars)
            cond_text = source_text[idx:idx+80].strip()
            # Trim trailing punctuation
            cond_text = re.sub(r"[\s|;:,:\-–—]+$", "", cond_text)
            if len(cond_text) > 3:
                return cond_text
    
    return None


def determine_status(p: dict) -> str:
    """Determine status based on validation rules."""
    st = (p.get("source_text") or "").strip()
    
    # Placeholder check
    if st in ("", "-", "—", "N/A", "n/a", "typ", "–"):
        return "needs_review"
    
    # Get value
    val = p.get("typ") or p.get("value") or p.get("min") or p.get("max")
    val_str = str(val) if val is not None else ""
    has_value = val_str.strip() not in ("", "-", "—", "N/A", "None", "null")
    
    if not has_value:
        return "needs_review"
    
    # Get unit
    has_unit = p.get("unit") and str(p.get("unit")).strip() not in ("", "-", "—", "None", "null")
    
    # Known params that need condition
    needs_cond = {
        "Ciss", "Coss", "Crss", "QG", "QGS", "QGD", "Eon", "Eoff", "Err",
        "RDS(on)", "Rth JC", "Rth JH", "trr", "QRR", "IRRM", "VF",
        "VGS", "VDS", "ID", "IDSS", "gfs", "RG(int)",
    }
    sym = p.get("symbol", "")
    needs_cond_flag = sym in needs_cond
    
    has_condition = p.get("condition") and str(p["condition"]).strip() not in ("", "-", "—", "None", "null")
    
    # Known canonical params
    known_params = {
        "Ciss", "Coss", "Crss", "QGS", "QGD", "QG", "Eon", "Eoff", "Err",
        "RDS(on)", "Rth JC", "Rth JH",
        "trr", "QRR", "IRRM", "VF",
        "VDS", "VGS", "VGS(th)", "V(BR)DSS", "VGS(max)",
        "ID", "IDSS", "IGSS", "IDM", "IF", "IR", "gfs", "RG(int)",
        "Visol", "Clearance", "Creepage", "Weight", "Lstray",
        "TC", "TJ", "TVJ", "PD", "EON", "EOFF",
    }
    
    norm_sym = canonicalize_symbol(sym) if sym else ""
    is_known = sym in known_params or norm_sym in known_params
    
    # Determine status
    if is_known:
        if has_value:
            if needs_cond_flag and not has_condition:
                return "needs_alias_review"  # has value but missing condition
            if has_unit:
                return "confirmed"
            return "needs_alias_review"  # known param but unit missing
        return "needs_review"
    
    # Not a known canonical param
    if has_value:
        return "needs_alias_review"
    return "needs_review"


def normalize_ai_parameters(parameters: list) -> list:
    """
    Normalize AI-extracted parameters.
    
    Returns a new list with normalized fields, status recalculated,
    and normalization_notes added.
    """
    stats = {
        "unit_fixed": 0,
        "symbol_alias_fixed": 0,
        "symbol_inferred": 0,
        "condition_fixed": 0,
        "value_to_typ": 0,
        "pipe_parsed": 0,
    }
    
    normalized = []
    
    for param in parameters:
        if not isinstance(param, dict):
            continue
        
        p = dict(param)
        all_notes = []
        
        # Fix fields
        p, notes = fix_missing_fields(p)
        for n in notes:
            all_notes.append(n)
            if n.startswith("unit_from"):
                stats["unit_fixed"] += 1
            elif n == "symbol_from_pipe":
                stats["symbol_inferred"] += 1
            elif n.startswith("symbol_alias"):
                stats["symbol_alias_fixed"] += 1
            elif n.startswith("symbol_inferred"):
                stats["symbol_inferred"] += 1
            elif n == "condition_from_pipe" or n == "condition_inferred":
                stats["condition_fixed"] += 1
            elif n == "value_to_typ":
                stats["value_to_typ"] += 1
            elif "from_pipe" in n:
                stats["pipe_parsed"] += 1
        
        # Recalculate status
        old_status = p.get("status", "unknown")
        new_status = determine_status(p)
        if old_status != new_status:
            all_notes.append(f"status:{old_status}->{new_status}")
        
        p["status"] = new_status
        p["normalization_notes"] = all_notes
        
        # Ensure all keys exist
        for key in ["category", "section", "symbol", "parameter", "min", "typ",
                     "max", "value", "unit", "condition", "source_page",
                     "source_text", "confidence"]:
            if key not in p:
                p[key] = None
        
        normalized.append(p)
    
    normalized.append({"_normalizer_stats": stats})
    return normalized


def extract_stats(normalized: list) -> dict:
    """Extract stats from normalized output."""
    if normalized and isinstance(normalized[-1], dict) and "_normalizer_stats" in normalized[-1]:
        return normalized[-1].pop("_normalizer_stats")
    return {}
