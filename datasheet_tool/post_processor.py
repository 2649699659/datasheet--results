"""
post_processor.py — Step 2.5: Post-processing fixes

Handles automatic fixes for common extraction issues:
1. Fix single-value parameters incorrectly placed in "min" field
2. Deduplicate parameters with same symbol and condition
3. Infer missing symbols for dimension parameters

Input:  list[Parameter], DocumentInfo
Output: list[Parameter] (with fixes applied)
"""

import logging
import re
from typing import List, Dict, Tuple

from .models import Parameter

logger = logging.getLogger(__name__)


def _normalize_condition(cond: str) -> str:
    """Normalize condition string for comparison."""
    if not cond:
        return ""
    # Remove spaces, lowercase
    return re.sub(r'\s+', '', cond.lower())


def _conditions_similar(cond1: str, cond2: str) -> bool:
    """Check if two conditions are similar enough to be considered duplicates."""
    norm1 = _normalize_condition(cond1)
    norm2 = _normalize_condition(cond2)
    
    if norm1 == norm2:
        return True
    
    # Check if one is a substring of the other
    if norm1 in norm2 or norm2 in norm1:
        return True
    
    # Check key parameters match
    key_params = ['vgs', 'vds', 'id', 'ic', 'tc', 'tj', 'vdd', 'vr', 'rg']
    keys1 = set(re.findall(r'(?:vgs|vds|id|ic|tc|tj|vdd|vr|rg)\s*[=<>]\s*\S+', norm1))
    keys2 = set(re.findall(r'(?:vgs|vds|id|ic|tc|tj|vdd|vr|rg)\s*[=<>]\s*\S+', norm2))
    
    if keys1 and keys2 and keys1 == keys2:
        return True
    
    return False


def _symbols_match(sym1: str, sym2: str) -> bool:
    """Check if two symbols are similar enough to be duplicates."""
    if not sym1 or not sym2:
        return False
    
    # Direct match
    if sym1.lower() == sym2.lower():
        return True
    
    # Normalize common variations
    norm1 = re.sub(r'[()\s]', '', sym1.lower())
    norm2 = re.sub(r'[()\s]', '', sym2.lower())
    if norm1 == norm2:
        return True
    
    return False


def fix_single_value_in_min(parameters: List[Parameter]) -> List[Parameter]:
    """
    Fix parameters where a single value is incorrectly in "min" field.
    
    For parameters that have:
    - min has a value
    - typ, max are None/empty
    - value is None/empty
    
    Move min to value.
    """
    fixed_count = 0
    for p in parameters:
        has_min = p.min is not None and p.min != ""
        has_value = p.value is not None and p.value != ""
        has_typ = p.typ is not None and p.typ != ""
        has_max = p.max is not None and p.max != ""
        
        # If only min has a value and it's a single value parameter
        if has_min and not has_value and not has_typ and not has_max:
            # Check if this is a single-value parameter (not a range)
            # Single value parameters: breakdown voltage, thresholds, etc.
            # We move min to value for these
            p.value = p.min
            p.min = None
            fixed_count += 1
            logger.debug(f"Fixed {p.symbol}: moved min({p.value}) to value")
    
    if fixed_count > 0:
        logger.info(f"Fixed {fixed_count} single-value parameters")
    
    return parameters


def deduplicate_parameters(parameters: List[Parameter]) -> List[Parameter]:
    """
    Remove duplicate parameters based on symbol and condition.
    
    Keep the one with higher confidence or more complete data.
    """
    seen: List[Tuple[str, str, int]] = []  # (symbol_norm, condition_norm, index)
    duplicates: List[int] = []
    
    for i, p in enumerate(parameters):
        sym_norm = re.sub(r'[()\s]', '', (p.symbol or "").lower())
        cond_norm = _normalize_condition(p.condition)
        
        # Check if we've seen this symbol+condition combination
        is_duplicate = False
        for sym_s, cond_s, idx_s in seen:
            if _symbols_match(p.symbol or "", parameters[idx_s].symbol or "") and _conditions_similar(p.condition or "", parameters[idx_s].condition or ""):
                is_duplicate = True
                
                # Keep the one with higher confidence or more complete data
                existing = parameters[idx_s]
                
                # Compare completeness
                existing_fields = sum([1 for x in [existing.value, existing.min, existing.typ, existing.max] if x is not None and x != ""])
                new_fields = sum([1 for x in [p.value, p.min, p.typ, p.max] if x is not None and x != ""])
                
                # If new one has more data, mark existing as duplicate
                if new_fields > existing_fields:
                    duplicates.append(idx_s)
                    seen[idx_s] = (sym_norm, cond_norm, i)  # Update to new index
                else:
                    duplicates.append(i)
                
                break
        
        if not is_duplicate:
            seen.append((sym_norm, cond_norm, i))
    
    if duplicates:
        logger.info(f"Deduplication: removing {len(duplicates)} duplicate parameters")
        parameters = [p for i, p in enumerate(parameters) if i not in duplicates]
    
    return parameters


def _infer_dimension_symbol(p: Parameter) -> str:
    """
    Try to infer the symbol for a dimension parameter with missing symbol.
    
    Looks at unit and condition to determine appropriate symbol.
    """
    unit = (p.unit or "").lower().strip()
    cond = (p.condition or "").lower()
    
    # Get numeric value for context
    value_str = ""
    if p.value:
        value_str = str(p.value)
    elif p.min:
        value_str = str(p.min)
    elif p.typ:
        value_str = str(p.typ)
    
    # Infer based on unit
    if unit in ["mm", "millimeter", "millimeters"]:
        # Dimension parameters - infer from condition and value
        if "terminal to terminal" in cond or "tt" in cond:
            if float(value_str or 0) < 15:
                return "Dtt_gate_emitter"  # Gate-Emitter terminal spacing
            else:
                return "Dtt"  # General terminal-to-terminal
        elif "terminal to baseplate" in cond or "tb" in cond:
            return "Dtb"  # Terminal to baseplate
        elif "clearance" in cond:
            return "Clearance"
        elif "creepage" in cond:
            return "Creepage"
        else:
            return "Dimension"
    
    elif unit in ["nm", "n·m", "n.m"]:
        # Torque parameters
        if "m6" in cond or "m8" in cond:
            return "Torque"
        else:
            return "MountingTorque"
    
    elif unit in ["g", "gram", "grams"]:
        return "Weight"
    
    elif unit in ["kV", "kv"]:
        return "Visol"  # Isolation voltage
    
    return ""


def fix_missing_symbols(parameters: List[Parameter]) -> List[Parameter]:
    """
    Fix parameters with missing symbols.
    
    For parameters where symbol is None/empty, try to infer from context.
    """
    fixed_count = 0
    
    for p in parameters:
        if not p.symbol or p.symbol.strip() == "" or p.symbol == "-":
            inferred = _infer_dimension_symbol(p)
            if inferred:
                p.symbol = inferred
                p.needs_review = True  # Mark for review since inference may not be perfect
                fixed_count += 1
                logger.debug(f"Inferred symbol '{inferred}' for parameter with condition: {p.condition}")
    
    if fixed_count > 0:
        logger.info(f"Fixed {fixed_count} missing symbols (marked for review)")
    
    return parameters


def post_process(parameters: List[Parameter]) -> List[Parameter]:
    """
    Apply all post-processing fixes.
    
    Order matters:
    1. Fix single-value in min field
    2. Deduplicate
    3. Fix missing symbols
    """
    logger.info("Post-processing parameters...")
    
    # Step 1: Fix single-value parameters
    parameters = fix_single_value_in_min(parameters)
    
    # Step 2: Deduplicate
    parameters = deduplicate_parameters(parameters)
    
    # Step 3: Fix missing symbols
    parameters = fix_missing_symbols(parameters)
    
    logger.info(f"Post-processing complete: {len(parameters)} parameters")
    
    return parameters


if __name__ == "__main__":
    import json
    import sys
    
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
    if len(sys.argv) < 2:
        print("Usage: python3 post_processor.py <json_file>")
        sys.exit(1)
    
    from .models import ExtractionResult
    
    json_path = sys.argv[1]
    result = ExtractionResult.load_json(json_path)
    
    print(f"Loaded {len(result.parameters)} parameters")
    
    # Apply post-processing
    result.parameters = post_process(result.parameters)
    
    # Save
    output_path = json_path.replace("_extracted.json", "_postprocessed.json")
    result.save_json(output_path)
    print(f"Saved to {output_path}")
