"""
Table Candidate Parser

Extracts candidate parameter rows from valid tables using alias matching.

Functions:
    - parse_table_candidates(extracted_pdf, target_fields) -> List[RawExtractedParam]

Match Types:
    - exact_match: confidence 0.95
    - normalized_symbol_match: confidence 0.85
    - fuzzy_match: confidence 0.70
"""

import re
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Set

from rapidfuzz import fuzz

from pipeline.models import RawExtractedParam, ParamStatus, ExtractionMethod


# Match type enum-like constants
MATCH_EXACT = "exact_match"
MATCH_SYMBOL = "normalized_symbol_match"
MATCH_FUZZY = "fuzzy_match"

# Confidence scores
CONFIDENCE_EXACT = 0.95
CONFIDENCE_SYMBOL = 0.85
CONFIDENCE_FUZZY = 0.70

# Fuzzy threshold
FUZZY_THRESHOLD = 88

# Minimum alias length for fuzzy matching
MIN_FUZZY_ALIAS_LEN = 3

# Short symbol aliases that only allow exact/symbol match
SHORT_SYMBOLS = {"qg", "qgs", "qgd", "id", "ic", "vds", "vgs", "rg"}


def normalize_symbol(text: str) -> str:
    """
    Normalize symbol by removing special characters and spaces.
    
    Examples:
        "RDS(on)" -> "rdson"
        "VGS(th)" -> "vgsth"
        "QGD" -> "qgd"
    """
    # Remove parentheses, hyphens, underscores, spaces
    text = re.sub(r"[\(\)\-\_\s\.]+", "", text)
    return text.lower()


def clean_row_text(row: List[str]) -> str:
    """
    Clean a table row by concatenating cells and normalizing whitespace.
    """
    # Convert all cells to string
    cells = [str(cell) if cell is not None else "" for cell in row]
    # Join with single space
    text = " ".join(cells)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def is_empty_row(row_text: str) -> bool:
    """Check if a row is effectively empty."""
    return len(row_text.strip()) < 2


def generate_source_hash(source_text: str, document_id: str, page: int, table_idx: int, row_idx: int) -> str:
    """Generate a stable hash for the source."""
    hash_input = f"{source_text}:{document_id}:{page}:{table_idx}:{row_idx}"
    return hashlib.sha256(hash_input.encode()).hexdigest()[:16]


def is_short_alias(alias: str) -> bool:
    """Check if alias is a short symbol that should not use fuzzy matching."""
    normalized = normalize_symbol(alias)
    return normalized in SHORT_SYMBOLS or len(alias) < MIN_FUZZY_ALIAS_LEN


def check_exact_match(alias: str, row_text: str) -> bool:
    """
    Check if alias appears exactly in row_text (case-insensitive).
    """
    alias_lower = alias.lower()
    row_lower = row_text.lower()
    return alias_lower in row_lower


def check_normalized_symbol_match(alias: str, row_text: str) -> bool:
    """
    Check if normalized alias matches any normalized token in row_text.
    
    Handles variations like:
        RDS(on), RDSon, R_DS(on) -> all match
        VGS(th), Vth -> match
    """
    norm_alias = normalize_symbol(alias)
    
    # Normalize the entire row text
    norm_row = normalize_symbol(row_text)
    
    # Check if normalized alias is in normalized row
    if norm_alias in norm_row:
        return True
    
    # Additional check: split row into tokens and check
    # This handles cases where symbols are separated
    row_tokens = re.findall(r'[a-zA-Z]+', norm_row)
    if norm_alias in row_tokens:
        return True
    
    return False


def check_fuzzy_match(alias: str, row_text: str) -> Tuple[bool, float]:
    """
    Check if alias fuzzy-matches any part of row_text.
    
    Returns:
        (is_match, score)
    """
    # Don't use fuzzy for short aliases
    if is_short_alias(alias):
        return False, 0.0
    
    # Tokenize row_text to find best match
    # Split into tokens and check each
    tokens = re.findall(r'\b\w+\b', row_text)
    
    best_score = 0.0
    for token in tokens:
        if len(token) >= len(alias) - 1:  # Length sanity check
            score = fuzz.ratio(alias.lower(), token.lower())
            if score >= FUZZY_THRESHOLD:
                best_score = max(best_score, score)
    
    return best_score >= FUZZY_THRESHOLD, best_score


def find_best_match(aliases: List[str], row_text: str) -> Tuple[Optional[str], Optional[str], Optional[float]]:
    """
    Find the best match type and alias for a row.
    
    Returns:
        (matched_alias, match_type, confidence)
    """
    best_result = None  # (alias, match_type, confidence)
    
    for alias in aliases:
        # Skip empty aliases
        if not alias or not alias.strip():
            continue
            
        # 1. Try exact match first (highest priority)
        if check_exact_match(alias, row_text):
            if best_result is None or CONFIDENCE_EXACT > best_result[2]:
                best_result = (alias, MATCH_EXACT, CONFIDENCE_EXACT)
            continue
        
        # 2. Try normalized symbol match
        if check_normalized_symbol_match(alias, row_text):
            if best_result is None or CONFIDENCE_SYMBOL > best_result[2]:
                best_result = (alias, MATCH_SYMBOL, CONFIDENCE_SYMBOL)
            continue
        
        # 3. Try fuzzy match (only for longer aliases)
        if not is_short_alias(alias):
            is_match, score = check_fuzzy_match(alias, row_text)
            if is_match:
                if best_result is None or CONFIDENCE_FUZZ > best_result[2]:
                    best_result = (alias, MATCH_FUZZ, CONFIDENCE_FUZZ)
    
    if best_result:
        return best_result[0], best_result[1], best_result[2]
    return None, None, None


def is_false_positive(field_id: str, row_text: str, matched_alias: str) -> bool:
    """
    Check if a match is likely a false positive.
    
    Returns True if this should NOT be a candidate.
    """
    row_lower = row_text.lower()
    
    # Rule: Visol should not match "Voltage Rating" category
    if field_id == "visol" or field_id == "isol":
        # Only match if isolation-related terms are present
        isolation_terms = ["isolation", "visol", "dielectric", "isolation voltage"]
        if not any(term in row_lower for term in isolation_terms):
            # But allow if it's clearly not voltage rating context
            if "voltage" in row_lower and "rating" in row_lower:
                return True  # False positive - it's a voltage rating
    
    # Rule: Rth JC vs Rth JH disambiguation
    if field_id in ("rth_jc", "rth_jh"):
        jc_terms = ["junction-case", "junction to case", "jc", "case"]
        jh_terms = ["junction-heatsink", "junction to heat", "jh", "heatsink", "heat sink"]
        
        jc_score = sum(1 for t in jc_terms if t in row_lower)
        jh_score = sum(1 for t in jh_terms if t in row_lower)
        
        # If we have a strong mismatch, reject
        if field_id == "rth_jc" and jc_score == 0 and jh_score > 1:
            return True
        if field_id == "rth_jh" and jh_score == 0 and jc_score > 1:
            return True
    
    # Rule: Clearance/Creepage without T-T/T-B info
    if field_id in ("clearance_tt", "clearance_tb", "creepage_tt", "creepage_tb"):
        # Check if T-T or T-B is mentioned
        tt_mentioned = "t-t" in row_lower or "terminal to terminal" in row_lower
        tb_mentioned = "t-b" in row_lower or "terminal to baseplate" in row_lower or "baseplate" in row_lower
        
        # If neither T-T nor T-B is mentioned, mark as unclear
        # This is handled in review_reason, not rejection
        pass  # Allow but flag in review_reason
    
    return False


def should_reject_rating_candidate(
    field_id: str,
    row_text: str,
    matched_alias: str
) -> Optional[str]:
    """
    Check if current_rating or voltage_rating candidate should be rejected.
    
    Returns rejection reason string if should be rejected, None if acceptable.
    
    This is a conservative guard to prevent overmatching on broad aliases.
    """
    if field_id not in ("current_rating", "voltage_rating"):
        return None
    
    row_lower = row_text.lower()
    alias_lower = matched_alias.lower()
    
    if field_id == "current_rating":
        # === STRICT REJECTION RULES for current_rating ===
        
        # Rejection patterns - these ALWAYS reject
        reject_patterns = [
            ("irrm", "reverse_recovery_current_not_rating"),
            ("ifsm", "surge_current_not_rating"),
            ("qrr", "reverse_recovery_charge_not_rating"),
            ("test condition", "test_condition_not_rating"),
            ("gate current", "gate_current_not_rating"),
            ("leakage current", "leakage_current_not_rating"),
            ("reverse current", "reverse_current_not_rating"),
            ("short circuit", "short_circuit_not_rating"),
            ("switching condition", "switching_condition_not_rating"),
            ("forward current", "forward_current_not_rating"),
            ("output current", "output_current_not_rating"),
            ("input current", "input_current_not_rating"),
        ]
        
        for pattern, reason in reject_patterns:
            if pattern in row_lower:
                return reason
        
        # Special case: "current" alone without strong context is too broad
        if alias_lower == "current":
            # Allow ONLY if strong semantic context present
            strong_contexts = [
                "current rating",
                "rated current",
                "nominal current",
                "continuous current",
                "module current",
                "maximum current",
                "drain current",
            ]
            if not any(ctx in row_lower for ctx in strong_contexts):
                return "too_broad_without_context"
        
        # Special case: "ic" alone is too broad (often appears in "static characteristics")
        if alias_lower == "ic":
            # Reject if just "IC" appears without strong current context
            if "current" not in row_lower and "drain" not in row_lower:
                return "IC_too_broad_without_current_context"
        
        # Special case: "id" alone is too broad
        if alias_lower == "id":
            # Allow only if strong context present
            strong_contexts = [
                "drain current",
                "continuous current",
                "rated current",
                "maximum current",
                "nominal current",
            ]
            if not any(ctx in row_lower for ctx in strong_contexts):
                return "ID_too_broad_without_context"
        
        return None
    
    if field_id == "voltage_rating":
        # === STRICT REJECTION RULES for voltage_rating ===
        
        # Rejection patterns - these ALWAYS reject
        reject_patterns = [
            ("visol", "isolation_voltage_not_rating"),
            ("isolation voltage", "isolation_voltage_not_rating"),
            ("vth", "threshold_voltage_not_rating"),
            ("gate voltage", "gate_voltage_not_rating"),
            ("gate-source voltage", "gate_voltage_not_rating"),
            ("test condition", "test_condition_not_rating"),
            ("vds=", "test_condition_vds_not_rating"),
            ("vgs=", "test_condition_vgs_not_rating"),
            ("output voltage", "output_voltage_not_rating"),
            ("input voltage", "input_voltage_not_rating"),
        ]
        
        for pattern, reason in reject_patterns:
            if pattern in row_lower:
                return reason
        
        # Special case: "voltage" alone without strong context is too broad
        if alias_lower == "voltage":
            strong_contexts = [
                "voltage rating",
                "rated voltage",
                "blocking voltage",
                "drain-source voltage",
                "breakdown voltage",
                "maximum voltage",
                "module voltage",
                "vds rating",
            ]
            if not any(ctx in row_lower for ctx in strong_contexts):
                return "too_broad_without_context"
        
        # Special case: "vds" alone can match VGS (gate-source voltage)
        if alias_lower == "vds" or alias_lower == "vdss":
            # Reject if it's actually about gate or test conditions
            if "gate" in row_lower:
                return "gate_voltage_not_rating"
            if "vgs" in row_lower:
                return "gate_voltage_not_rating"
        
        return None
    
    return None


def get_rating_accept_reason(
    field_id: str,
    row_text: str,
    matched_alias: str
) -> str:
    """
    Determine why a current_rating or voltage_rating candidate was accepted.
    
    Returns accept reason string based on what context was found.
    """
    if field_id not in ("current_rating", "voltage_rating"):
        return ""
    
    row_lower = row_text.lower()
    alias_lower = matched_alias.lower()
    
    if field_id == "current_rating":
        # Check what made it pass
        if "continuous current" in row_lower:
            return "matched_continuous_current"
        if "rated current" in row_lower or "current rating" in row_lower:
            return "matched_rated_current"
        if "nominal current" in row_lower:
            return "matched_nominal_current"
        if "maximum current" in row_lower or "max current" in row_lower:
            return "matched_maximum_current"
        if "module current" in row_lower:
            return "matched_module_current"
        if "drain current" in row_lower:
            return "matched_drain_current"
        # For ID and IC, if we got here, they had strong context
        if alias_lower in ("id", "ic"):
            return "strong_current_context"
        return "strong_rating_context"
    
    if field_id == "voltage_rating":
        # Check what made it pass
        if "blocking voltage" in row_lower:
            return "matched_blocking_voltage"
        if "breakdown voltage" in row_lower:
            return "matched_breakdown_voltage"
        if "rated voltage" in row_lower or "voltage rating" in row_lower:
            return "matched_rated_voltage"
        if "maximum voltage" in row_lower or "max voltage" in row_lower:
            return "matched_maximum_voltage"
        if "module voltage" in row_lower:
            return "matched_module_voltage"
        if "drain-source voltage" in row_lower:
            return "matched_drain_source_voltage"
        return "strong_rating_context"
    
    return ""


def get_review_reason(field_id: str, row_text: str, matched_alias: str, match_type: str) -> str:
    """
    Generate appropriate review_reason based on field type and match quality.
    """
    row_lower = row_text.lower()
    
    # Clearance/Creepage condition check
    if field_id in ("clearance_tt", "clearance_tb", "creepage_tt", "creepage_tb"):
        tt_mentioned = "t-t" in row_lower or "terminal to terminal" in row_lower
        tb_mentioned = "t-b" in row_lower or "terminal to baseplate" in row_lower or "baseplate" in row_lower
        
        if field_id.endswith("_tt") and not tt_mentioned and not tb_mentioned:
            return "condition_unclear: clearance/creepage T-T unspecified"
        if field_id.endswith("_tb") and not tt_mentioned and not tb_mentioned:
            return "condition_unclear: clearance/creepage T-B unspecified"
    
    # Fuzzy match always needs review
    if match_type == MATCH_FUZZY:
        return "candidate_row_only_value_not_parsed:fuzzy_match_needs_review"
    
    # Default reason for all candidates in this phase
    return "candidate_row_only_value_not_parsed"


def parse_table_candidates(extracted_pdf: Dict[str, Any], target_fields: List[Dict[str, Any]]) -> Tuple[List[RawExtractedParam], Dict[str, Any]]:
    """
    Parse valid tables to find candidate parameter rows.
    
    Args:
        extracted_pdf: Output from extractor.py with document_id, pdf_stem, pages
        target_fields: List of field configs from config_loader.py
        
    Returns:
        Tuple of (List of RawExtractedParam candidates, Dict of rejected info)
    """
    candidates = []
    rejected_info = {}  # Track rejected candidates by rating guard
    
    document_id = extracted_pdf.get("document_id", "")
    pdf_path = extracted_pdf.get("pdf_path", "")
    file_name = extracted_pdf.get("file_name", "")
    pdf_stem = extracted_pdf.get("pdf_stem", "")
    
    # Build field lookup
    field_lookup = {f["id"]: f for f in target_fields}
    
    # Track which fields have been matched
    matched_fields = set()
    
    for page_data in extracted_pdf.get("pages", []):
        page_num = page_data.get("page_number", 0)
        text = page_data.get("text", "")
        
        for table_data in page_data.get("tables", []):
            table_idx = table_data.get("table_index", -1)
            table_status = table_data.get("status", "")
            
            # Only process valid tables
            if table_status != "valid":
                continue
            
            rows = table_data.get("rows", [])
            
            for row_idx, row in enumerate(rows):
                # Clean row text
                row_text = clean_row_text(row)
                
                # Skip empty rows
                if is_empty_row(row_text):
                    continue
                
                # Try to match each field
                for field in target_fields:
                    field_id = field["id"]
                    label = field.get("label", "")
                    unit = field.get("unit", "")
                    category = field.get("category", "uncategorized")
                    priority = field.get("priority", "medium")
                    applies_to = field.get("applies_to", ["module", "discrete_mosfet", "die", "unknown"])
                    aliases = field.get("aliases", [])
                    # Matching policy fields (Step 4.7)
                    match_strategy = field.get("match_strategy", "normal")
                    
                    # Skip if no aliases
                    if not aliases:
                        continue
                    
                    # Find best match
                    matched_alias, match_type, confidence = find_best_match(aliases, row_text)
                    
                    if matched_alias is None:
                        continue  # No match for this field in this row
                    
                    # Check for false positives
                    if is_false_positive(field_id, row_text, matched_alias):
                        continue
                    
                    # Check rating guard for current_rating and voltage_rating
                    rejection_reason = should_reject_rating_candidate(field_id, row_text, matched_alias)
                    if rejection_reason is not None:
                        # Track rejected candidate (Step 4.7: add new fields)
                        rejected_key = (field_id, matched_alias, rejection_reason)
                        if rejected_key not in rejected_info:
                            rejected_info[rejected_key] = {
                                "field_id": field_id,
                                "label": label,
                                "matched_alias": matched_alias,
                                "match_type": match_type,
                                "match_policy": match_strategy,
                                "candidate_status": "rejected",
                                "accept_reason": "",
                                "rejection_reason": rejection_reason,
                                "count": 0,
                                "examples": []
                            }
                        rejected_info[rejected_key]["count"] += 1
                        if len(rejected_info[rejected_key]["examples"]) < 3:
                            rejected_info[rejected_key]["examples"].append({
                                "source_page": page_num,
                                "table_index": table_idx,
                                "row_index": row_idx,
                                "source_text": row_text[:200]
                            })
                        continue  # Reject this candidate
                    
                    # Generate review reason
                    review_reason = get_review_reason(field_id, row_text, matched_alias, match_type)
                    
                    # Get accept_reason for rating fields (Step 4.7)
                    accept_reason = get_rating_accept_reason(field_id, row_text, matched_alias) if field_id in ("current_rating", "voltage_rating") else ""
                    
                    # Capture row structure for value parsing (Step 5)
                    row_cells = row  # The actual row cells
                    row_cell_count = len(row_cells)
                    
                    # Get nearby header rows (up to 3 rows before)
                    nearby_headers = []
                    header_start = max(0, row_idx - 3)
                    for hrow_idx in range(header_start, row_idx):
                        if hrow_idx < len(rows):
                            nearby_headers.append(rows[hrow_idx])
                    
                    # Get previous and next row text
                    prev_row_text = ""
                    next_row_text = ""
                    if row_idx > 0 and row_idx - 1 < len(rows):
                        prev_row_text = clean_row_text(rows[row_idx - 1])
                    if row_idx + 1 < len(rows):
                        next_row_text = clean_row_text(rows[row_idx + 1])
                    
                    # Create candidate (Step 4.7: add matching strategy fields, Step 5: add row structure)
                    candidate = RawExtractedParam(
                        document_id=document_id,
                        pdf_path=pdf_path,
                        file_name=file_name,
                        pdf_stem=pdf_stem,
                        part_number="",  # To be filled later
                        manufacturer="",  # To be filled later
                        field_id=field_id,
                        label=label,
                        category=category,
                        priority=priority,
                        applies_to=applies_to,
                        symbol=matched_alias,
                        parameter=label,
                        unit=unit,
                        original_unit="",
                        normalized_unit=unit,
                        source_page=page_num,
                        table_index=table_idx,
                        row_index=row_idx,
                        source_text=row_text,
                        source_hash=generate_source_hash(row_text, document_id, page_num, table_idx, row_idx),
                        confidence=confidence,
                        status=ParamStatus.NEEDS_REVIEW,
                        method=ExtractionMethod.RULE_TABLE,
                        review_reason=review_reason,
                        # Matching Strategy Fields (Step 4.7)
                        match_type=match_type,
                        match_policy=match_strategy,
                        accept_reason=accept_reason,
                        reject_reason="",
                        candidate_status="active",
                        # Row Structure (Step 5)
                        row_cells=row_cells,
                        row_cell_count=row_cell_count,
                        nearby_header_rows=nearby_headers,
                        previous_row_text=prev_row_text,
                        next_row_text=next_row_text,
                        condition="",  # To be filled by value_parser
                    )
                    
                    candidates.append(candidate)
                    matched_fields.add(field_id)
    
    return candidates, rejected_info


def candidates_to_debug_json(
    candidates: List[RawExtractedParam],
    extracted_pdfs: List[Dict[str, Any]],
    all_target_field_ids: Set[str],
    all_rejected: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convert candidates to the debug JSON structure.
    
    Args:
        candidates: List of candidate RawExtractedParam
        extracted_pdfs: List of extracted PDF info dicts
        all_target_field_ids: Complete set of target field IDs
        all_rejected: Optional dict of rejected candidate info
    """
    pdf_lookup = {pdf.get("document_id", ""): pdf for pdf in extracted_pdfs}
    
    # Group candidates by document
    by_doc: Dict[str, List[RawExtractedParam]] = {}
    
    for c in candidates:
        doc_id = c.document_id
        if doc_id not in by_doc:
            by_doc[doc_id] = []
        by_doc[doc_id].append(c)
    
    pdfs_out = []
    for doc_id, doc_candidates in by_doc.items():
        pdf_info = pdf_lookup.get(doc_id, {})
        doc_matched_fields = set(c.field_id for c in doc_candidates)
        doc_unmatched_fields = all_target_field_ids - doc_matched_fields
        
        candidates_list = []
        for c in doc_candidates:
            candidates_list.append({
                "document_id": c.document_id,
                "file_name": c.file_name,
                "field_id": c.field_id,
                "label": c.label,
                "matched_alias": c.symbol,
                "match_type": (
                    MATCH_EXACT if c.confidence == CONFIDENCE_EXACT
                    else MATCH_SYMBOL if c.confidence == CONFIDENCE_SYMBOL
                    else MATCH_FUZZY
                ),
                "match_policy": c.match_policy,
                "candidate_status": c.candidate_status,
                "accept_reason": c.accept_reason,
                "reject_reason": c.reject_reason,
                "confidence": c.confidence,
                "source_page": c.source_page,
                "table_index": c.table_index,
                "row_index": c.row_index,
                "source_text": c.source_text,
                "source_hash": c.source_hash,
                "review_reason": c.review_reason,
                # Row Structure (Step 5)
                "row_cells": c.row_cells,
                "row_cell_count": c.row_cell_count,
                "nearby_header_rows": c.nearby_header_rows,
                "previous_row_text": c.previous_row_text,
                "next_row_text": c.next_row_text,
                "condition": c.condition,
            })
        
        pdfs_out.append({
            "document_id": doc_id,
            "file_name": pdf_info.get("file_name", ""),
            "pdf_stem": pdf_info.get("pdf_stem", ""),
            "target_field_count": len(all_target_field_ids),
            "matched_field_count": len(doc_matched_fields),
            "unmatched_field_count": len(doc_unmatched_fields),
            "matched_fields": sorted(doc_matched_fields),
            "unmatched_fields": sorted(doc_unmatched_fields),
            "candidate_count": len(doc_candidates),
            "candidates": candidates_list,
        })
    
    # Global matched/unmatched
    global_matched = set(c.field_id for c in candidates)
    global_unmatched = all_target_field_ids - global_matched
    
    # Compute rejected counts by field
    rejected_by_field = {}
    total_rejected = 0
    if all_rejected:
        for key, info in all_rejected.items():
            fid = info["field_id"]
            if fid not in rejected_by_field:
                rejected_by_field[fid] = 0
            rejected_by_field[fid] += info["count"]
            total_rejected += info["count"]
    
    return {
        "candidate_count": len(candidates),
        "active_candidate_count": len(candidates),  # All candidates in list are active (Step 4.7)
        "total_target_field_count": len(all_target_field_ids),
        "matched_field_count": len(global_matched),
        "unmatched_field_count": len(global_unmatched),
        "matched_fields": sorted(global_matched),
        "unmatched_fields": sorted(global_unmatched),
        "rejected_candidate_count": total_rejected,
        "rejected_by_rating_guard_count": total_rejected,
        "rejected_by_field": rejected_by_field,
        # Candidate Status Breakdown (Step 4.7)
        "candidate_status_breakdown": {
            "active": len(candidates),
            "rejected": total_rejected,
            "weak": 0,
        },
        "pdfs": pdfs_out,
    }


def generate_candidate_audit(
    candidates: List[RawExtractedParam],
    target_fields: List[Dict[str, Any]],
    debug_json: Dict[str, Any],
    all_rejected: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate candidate quality audit markdown report.
    
    Step 4.7: Enhanced with Field Source Expectation, Zero-Candidate Classification,
    Accepted/Rejected Rating Candidates, and Candidate Status Breakdown.
    
    Args:
        candidates: List of candidate RawExtractedParam
        target_fields: Complete target fields list
        debug_json: Debug JSON from candidates_to_debug_json
        all_rejected: Optional dict of rejected candidate info
        
    Returns:
        Markdown string for the audit report
    """
    # Build field lookup
    field_lookup = {f["id"]: f for f in target_fields}
    
    # Group candidates by field_id
    by_field: Dict[str, List[RawExtractedParam]] = {}
    for c in candidates:
        if c.field_id not in by_field:
            by_field[c.field_id] = []
        by_field[c.field_id].append(c)
    
    all_target_ids = set(f["id"] for f in target_fields)
    matched_ids = set(by_field.keys())
    zero_candidate_ids = all_target_ids - matched_ids
    
    # Compute warnings
    possible_overmatching_ids = []
    fuzzy_only_ids = []
    
    for field_id, field_candidates in by_field.items():
        # Check overmatching (> 8 candidates)
        if len(field_candidates) > 8:
            possible_overmatching_ids.append(field_id)
        
        # Check fuzzy only
        match_types = set()
        for c in field_candidates:
            if c.confidence == CONFIDENCE_EXACT:
                match_types.add("exact")
            elif c.confidence == CONFIDENCE_SYMBOL:
                match_types.add("symbol")
            elif c.confidence == CONFIDENCE_FUZZY:
                match_types.add("fuzzy")
        
        if "fuzzy" in match_types and "exact" not in match_types and "symbol" not in match_types:
            fuzzy_only_ids.append(field_id)
    
    # Sort by candidate count
    field_stats = []
    for field_id in sorted(by_field.keys(), key=lambda x: len(by_field[x]), reverse=True):
        field_candidates = by_field[field_id]
        label = field_lookup.get(field_id, {}).get("label", field_id)
        
        # Count match types
        exact_count = sum(1 for c in field_candidates if c.confidence == CONFIDENCE_EXACT)
        symbol_count = sum(1 for c in field_candidates if c.confidence == CONFIDENCE_SYMBOL)
        fuzzy_count = sum(1 for c in field_candidates if c.confidence == CONFIDENCE_FUZZY)
        
        # Pages appeared
        pages = sorted(set(c.source_page for c in field_candidates))
        
        # Build warnings
        warnings = []
        if field_id in possible_overmatching_ids:
            warnings.append("possible_overmatching")
        if field_id in fuzzy_only_ids:
            warnings.append("fuzzy_only_match")
        
        field_stats.append({
            "field_id": field_id,
            "label": label,
            "candidate_count": len(field_candidates),
            "exact_count": exact_count,
            "symbol_count": symbol_count,
            "fuzzy_count": fuzzy_count,
            "pages": pages,
            "warnings": warnings,
            "candidates": field_candidates,
            "field_config": field_lookup.get(field_id, {}),
        })
    
    # Add zero-candidate fields
    for field_id in sorted(zero_candidate_ids):
        label = field_lookup.get(field_id, {}).get("label", field_id)
        field_stats.append({
            "field_id": field_id,
            "label": label,
            "candidate_count": 0,
            "exact_count": 0,
            "symbol_count": 0,
            "fuzzy_count": 0,
            "pages": [],
            "warnings": [],
            "candidates": [],
            "field_config": field_lookup.get(field_id, {}),
        })
    
    # Build markdown
    lines = []
    lines.append("# Candidate Quality Audit")
    lines.append("")
    
    # Get status breakdown from debug_json
    status_breakdown = debug_json.get('candidate_status_breakdown', {})
    total_active = status_breakdown.get('active', len(candidates))
    total_rejected = status_breakdown.get('rejected', debug_json.get('rejected_by_rating_guard_count', 0))
    total_weak = status_breakdown.get('weak', 0)
    
    # Section 1: Candidate Status Breakdown (NEW - Step 4.7)
    lines.append("## 1. Candidate Status Breakdown")
    lines.append("")
    lines.append(f"| Status | Count |")
    lines.append(f"|--------|-------|")
    lines.append(f"| active | {total_active} |")
    lines.append(f"| rejected | {total_rejected} |")
    lines.append(f"| weak | {total_weak} |")
    lines.append(f"| **Total** | **{total_active + total_rejected + total_weak}** |")
    lines.append("")
    lines.append("*active = valid candidates for further processing*")
    lines.append("*rejected = rejected by rating guard or policy*")
    lines.append("*weak = weak matches reserved for review/LLM*")
    lines.append("")
    
    # Section 2: Overview
    lines.append("## 2. 总览")
    lines.append("")
    lines.append(f"| 指标 | 值 |")
    lines.append(f"|------|---|")
    lines.append(f"| Processed PDFs | {debug_json.get('pdfs', [{}])[0].get('file_name', 'N/A') if debug_json.get('pdfs') else 0} |")
    lines.append(f"| Total Target Fields | {debug_json.get('total_target_field_count', 0)} |")
    lines.append(f"| Active Candidates | {total_active} |")
    lines.append(f"| Matched Fields | {debug_json.get('matched_field_count', 0)} |")
    lines.append(f"| Unmatched Fields | {debug_json.get('unmatched_field_count', 0)} |")
    lines.append(f"| Rejected by Rating Guard | {total_rejected} |")
    lines.append(f"| Possible Overmatching | {len(possible_overmatching_ids)} |")
    lines.append(f"| Fuzzy Only Match | {len(fuzzy_only_ids)} |")
    lines.append("")
    
    # Show before/after for current_rating and voltage_rating
    rejected_by_field = debug_json.get('rejected_by_field', {})
    for fid in ['current_rating', 'voltage_rating']:
        after_count = len(by_field.get(fid, []))
        rejected_count = rejected_by_field.get(fid, 0)
        before_count = after_count + rejected_count
        if rejected_count > 0 or before_count > 0:
            lines.append(f"**{fid}**: {before_count} → {after_count} (rejected: {rejected_count})")
            lines.append("")
    
    # Section 3: Field Source Expectation Summary (NEW - Step 4.7)
    lines.append("## 3. Field Source Expectation Summary")
    lines.append("")
    lines.append(f"| Field ID | Label | expected_sources | match_strategy | allow_fuzzy |")
    lines.append(f"|----------|-------|-----------------|----------------|-------------|")
    for s in field_stats:
        fc = s.get("field_config", {})
        expected_sources = ", ".join(fc.get("expected_sources", ["table"]))
        match_strategy = fc.get("match_strategy", "normal")
        allow_fuzzy = "Yes" if fc.get("allow_fuzzy", True) else "No"
        lines.append(f"| {s['field_id']} | {s['label']} | {expected_sources} | {match_strategy} | {allow_fuzzy} |")
    lines.append("")
    
    # Section 4: Zero-Candidate Fields Classification (REVISED - Step 4.7)
    lines.append("## 4. Zero-Candidate Fields")
    lines.append("")
    zero_candidate_fields = [s for s in field_stats if s["candidate_count"] == 0]
    
    # Classify zero-candidate fields
    expected_from_metadata = []
    needs_alias_check = []
    
    for s in zero_candidate_fields:
        field_id = s["field_id"]
        fc = s.get("field_config", {})
        expected_sources = fc.get("expected_sources", ["table"])
        
        if "metadata" in expected_sources or "page_text" in expected_sources:
            expected_from_metadata.append(s)
        else:
            needs_alias_check.append(s)
    
    if expected_from_metadata:
        lines.append("### A. Expected from Text/Metadata (not table)")
        lines.append("")
        lines.append("*These fields are expected to come from metadata or page text, not table extraction.*")
        lines.append("")
        lines.append(f"| Field ID | Label | expected_sources |")
        lines.append(f"|----------|-------|-----------------|")
        for s in expected_from_metadata:
            fc = s.get("field_config", {})
            expected_sources = ", ".join(fc.get("expected_sources", ["table"]))
            lines.append(f"| {s['field_id']} | {s['label']} | {expected_sources} |")
        lines.append("")
    
    if needs_alias_check:
        lines.append("### B. Needs Alias or PDF Check")
        lines.append("")
        lines.append("*These fields have no candidates and may need alias expansion or PDF content check.*")
        lines.append("")
        lines.append(f"| Field ID | Label | expected_sources |")
        lines.append(f"|----------|-------|-----------------|")
        for s in needs_alias_check:
            fc = s.get("field_config", {})
            expected_sources = ", ".join(fc.get("expected_sources", ["table"]))
            lines.append(f"| {s['field_id']} | {s['label']} | {expected_sources} |")
        lines.append("")
    
    if not zero_candidate_fields:
        lines.append("All fields have at least one candidate.")
        lines.append("")
    
    # Section 5: Candidate Count by Field
    lines.append("## 5. Candidate Count by Field")
    lines.append("")
    lines.append(f"| Field ID | Label | Count | Exact | Symbol | Fuzzy | Pages | Warnings |")
    lines.append(f"|----------|-------|-------|-------|--------|-------|-------|----------|")
    for s in field_stats:
        warnings_str = ", ".join(s["warnings"]) if s["warnings"] else "-"
        pages_str = ", ".join(str(p) for p in s["pages"][:5])
        if len(s["pages"]) > 5:
            pages_str += "..."
        lines.append(
            f"| {s['field_id']} | {s['label']} | {s['candidate_count']} "
            f"| {s['exact_count']} | {s['symbol_count']} | {s['fuzzy_count']} "
            f"| {pages_str} | {warnings_str} |"
        )
    lines.append("")
    
    # Section 6: Accepted Rating Candidates (NEW - Step 4.7)
    lines.append("## 6. Accepted Rating Candidates")
    lines.append("")
    lines.append("*current_rating and voltage_rating candidates that passed the rating guard*")
    lines.append("")
    
    for fid in ['current_rating', 'voltage_rating']:
        if fid not in by_field:
            continue
        
        field_candidates = by_field[fid]
        label = field_lookup.get(fid, {}).get("label", fid)
        lines.append(f"### {fid} ({label})")
        lines.append("")
        lines.append(f"Total: {len(field_candidates)} accepted candidates")
        lines.append("")
        
        for c in field_candidates:
            match_type = (
                "exact" if c.confidence == CONFIDENCE_EXACT
                else "symbol" if c.confidence == CONFIDENCE_SYMBOL
                else "fuzzy"
            )
            source_text = c.source_text[:200]
            if len(c.source_text) > 200:
                source_text += "..."
            
            lines.append(f"**Page {c.source_page}, Table {c.table_index}, Row {c.row_index}**")
            lines.append(f"- matched_alias: `{c.symbol}`")
            lines.append(f"- match_type: {match_type}")
            lines.append(f"- match_policy: {c.match_policy}")
            lines.append(f"- accept_reason: {c.accept_reason or 'N/A'}")
            lines.append(f"- source_text: \"{source_text}\"")
            lines.append("")
    
    # Section 7: Rejected Rating Candidates
    if all_rejected:
        lines.append("## 7. Rejected Rating Candidates")
        lines.append("")
        lines.append("*current_rating and voltage_rating candidates rejected by rating guard*")
        lines.append("")
        
        # Group by field_id
        by_field_rejected = {}
        for key, info in all_rejected.items():
            fid = info["field_id"]
            if fid not in by_field_rejected:
                by_field_rejected[fid] = []
            by_field_rejected[fid].append(info)
        
        # Sort by total count
        for fid in sorted(by_field_rejected.keys(), key=lambda x: sum(i["count"] for i in by_field_rejected[x]), reverse=True):
            items = by_field_rejected[fid]
            total_count = sum(i["count"] for i in items)
            label = field_lookup.get(fid, {}).get("label", fid)
            lines.append(f"### {fid} ({label}) - {total_count} rejected")
            lines.append("")
            
            for item in items:
                lines.append(f"**Rejected by**: `{item['rejection_reason']}` (matched_alias: `{item['matched_alias']}`, count: {item['count']})")
                for ex in item.get("examples", [])[:3]:
                    source_text = ex.get("source_text", "")[:200]
                    lines.append(f"  - Page {ex.get('source_page')}, Table {ex.get('table_index')}, Row {ex.get('row_index')}: \"{source_text}\"")
                lines.append("")
            lines.append("")
    else:
        lines.append("## 7. Rejected Rating Candidates")
        lines.append("")
        lines.append("No candidates rejected by rating guard.")
        lines.append("")
    
    # Section 8: Candidate Examples by Field
    lines.append("## 8. Candidate Examples by Field")
    lines.append("")
    lines.append("*Each field shows up to 3 example candidates*")
    lines.append("")
    
    for s in field_stats:
        if not s["candidates"]:
            continue
        
        lines.append(f"### {s['field_id']} ({s['label']})")
        lines.append("")
        lines.append(f"Total: {s['candidate_count']} candidates | "
                    f"Exact: {s['exact_count']} | Symbol: {s['symbol_count']} | Fuzzy: {s['fuzzy_count']}")
        if s["warnings"]:
            lines.append(f"Warnings: {', '.join(s['warnings'])}")
        lines.append("")
        
        for c in s["candidates"][:3]:  # Max 3 examples
            match_type = (
                "exact" if c.confidence == CONFIDENCE_EXACT
                else "symbol" if c.confidence == CONFIDENCE_SYMBOL
                else "fuzzy"
            )
            source_text = c.source_text[:200]
            if len(c.source_text) > 200:
                source_text += "..."
            lines.append(f"**Page {c.source_page}, Table {c.table_index}, Row {c.row_index}**")
            lines.append(f"- matched_alias: `{c.symbol}`")
            lines.append(f"- match_type: {match_type}")
            lines.append(f"- match_policy: {c.match_policy}")
            if c.accept_reason:
                lines.append(f"- accept_reason: {c.accept_reason}")
            lines.append(f"- confidence: {c.confidence}")
            lines.append(f"- source_text: \"{source_text}\"")
            lines.append("")
        lines.append("")
    
    lines.append("")
    return "\n".join(lines)
