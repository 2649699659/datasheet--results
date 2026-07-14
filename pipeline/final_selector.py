"""
Final Selector v0 - Candidate Selection for Datasheet Extraction

Selects best candidate per field_id from parsed params and classifies as:
- final_candidate: Clean enough for Final Comparison
- review_needed: Has values but needs human review
- blocked: Dangerous/unusable candidates
- missing: No candidates found

Does NOT generate Excel. Pure selection logic.
"""

import json
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict


# =============================================================================
# Dangerous blockers - prevent Final directly
# =============================================================================
DANGEROUS_BLOCKERS = {
    "figure_caption_not_parameter_row",
    "unit_rejected_wrong_dimension",
    "condition_type_mismatch",
    "value_from_condition_rejected",
    "min_greater_than_max",
    "no_value_parsed",
    "vgs_th_missing_min_typ_max",
    "ambiguous_rating_row",  # high-risk for ratings
    "possible_test_condition_value",
}

# Soft warnings - do not block Final but reduce score
SOFT_WARNINGS = {
    "no_reliable_header": -5,
    "candidate_row_only_value_not_parsed": -2,
    "unit_not_found": -5,
    "unit_from_source_text_fallback": -3,
    "range_value_needs_review": -10,
    "slash_list_value_needs_review": -20,
    "partial_threshold_values": -10,
    "condition_unclear": -10,
}

# High-risk fields that should default to review_needed in v1
HIGH_RISK_FIELDS = {"current_rating", "voltage_rating"}


# =============================================================================
# Scoring Functions
# =============================================================================

def _has_value(param: Dict[str, Any]) -> bool:
    """Check if param has any value."""
    return any(param.get(k) is not None for k in ("value", "min", "typ", "max"))


def _has_preferred_value(param: Dict[str, Any], preferred: str) -> bool:
    """Check if param has the preferred value type."""
    if not preferred:
        return _has_value(param)
    return param.get(preferred) is not None


def _get_dangerous_blockers(param: Dict[str, Any]) -> List[str]:
    """Extract dangerous blockers from review_reason."""
    rr = param.get("review_reason", "") or ""
    return [b for b in DANGEROUS_BLOCKERS if b in rr]


def _get_soft_warnings(param: Dict[str, Any]) -> List[str]:
    """Extract soft warnings from review_reason."""
    rr = param.get("review_reason", "") or ""
    return [w for w in SOFT_WARNINGS if w in rr]


def _score_candidate(param: Dict[str, Any], field_config: Dict[str, Any]) -> Tuple[int, List[str], List[str]]:
    """
    Score a single candidate.
    
    Returns: (score, dangerous_blockers, soft_warnings)
    """
    score = 0
    blockers: List[str] = []
    soft: List[str] = []

    # --- parse_status base score ---
    status = param.get("parse_status", "failed")
    if status == "parsed":
        score += 30
    elif status == "partial":
        score += 20
    elif status == "unsafe":
        score -= 30
    elif status == "failed":
        score -= 50

    # --- parse_quality score ---
    quality = param.get("parse_quality", "low")
    if quality == "high":
        score += 25
    elif quality == "medium":
        score += 15
    elif quality == "low":
        score -= 20

    # --- value completeness ---
    preferred = field_config.get("preferred_value", "")
    if preferred and _has_preferred_value(param, preferred):
        score += 20
    elif _has_value(param):
        score += 10
    else:
        score -= 50

    # --- unit sanity ---
    unit_sanity = param.get("unit_sanity_status", "ok")
    if unit_sanity == "ok":
        score += 15
    elif unit_sanity == "missing":
        score += 0
    else:  # mismatch, rejected, etc.
        score -= 40

    # --- unit source ---
    unit_src = param.get("unit_source", "not_found")
    if unit_src == "unit_column":
        score += 10
    elif unit_src == "value_cell":
        score += 8
    elif unit_src in ("adjacent_cell", "split_cells"):
        score += 6
    elif unit_src == "source_text_fallback":
        score -= 5
    elif unit_src == "not_found":
        score -= 5
    elif unit_src.startswith("rejected_wrong_dimension"):
        score -= 80

    # --- dangerous blockers ---
    blockers = _get_dangerous_blockers(param)
    for b in blockers:
        if b == "figure_caption_not_parameter_row":
            score -= 100
        elif b == "unit_rejected_wrong_dimension":
            score -= 80
        elif b == "condition_type_mismatch":
            score -= 80
        elif b == "value_from_condition_rejected":
            score -= 80
        elif b == "ambiguous_rating_row":
            score -= 50
        elif b == "possible_test_condition_value":
            score -= 50
        elif b == "no_value_parsed":
            score -= 100
        elif b == "min_greater_than_max":
            score -= 60
        elif b == "vgs_th_missing_min_typ_max":
            score -= 80

    # --- soft warnings ---
    soft = _get_soft_warnings(param)
    for w in soft:
        score += SOFT_WARNINGS.get(w, -5)

    return score, blockers, soft


def _classify_field(
    params: List[Any],
    field_config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Classify a single field from its candidates.
    
    Returns a field selection dict.
    """
    field_id = field_config["id"]
    label = field_config.get("label", field_id)
    preferred = field_config.get("preferred_value", "")

    result = {
        "field_id": field_id,
        "label": label,
        "preferred_value": preferred,
        "selection_status": "missing",
        "selector_score": 0,
        "selector_reason": "",
        "selector_warnings": [],
        "selected_param": None,
        "review_params": [],
        "blocked_params": [],
        "candidate_count": 0,
        "review_params_count": 0,
        "blocked_params_count": 0,
    }

    # Ensure all params are dicts
    params = [_to_dict(p) for p in params]

    if not params:
        # Missing field
        result["selection_status"] = "missing"
        result["selector_reason"] = "no_candidates_in_parsed_params"
        result["selector_warnings"].append("missing_in_pdf" if field_id not in HIGH_RISK_FIELDS else "high_risk_field_no_candidates")
        return result

    result["candidate_count"] = len(params)

    # Score all candidates
    scored = []
    for p in params:
        s, blockers, soft = _score_candidate(p, field_config)
        scored.append((s, blockers, soft, p))

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_blockers, best_soft, best_param = scored[0]

    # Separate blocked vs review vs potential final
    blocked_params = []
    review_params = []

    for score, blockers, soft, p in scored:
        if blockers:
            blocked_params.append(p)
        elif score < 50:
            review_params.append(p)
        else:
            review_params.append(p)  # All go to review unless explicitly final

    # =======================================================================
    # Apply field-level special rules
    # =======================================================================

    # --- High-risk fields: current_rating, voltage_rating ---
    if field_id in HIGH_RISK_FIELDS:
        # Always review_needed in v1
        result["selection_status"] = "review_needed"
        result["selector_score"] = best_score
        result["selector_reason"] = "high_risk_rating_field_review_first"
        result["selector_warnings"] = best_soft.copy()
        result["selected_param"] = best_param
        result["review_params"] = review_params
        result["blocked_params"] = blocked_params
        result["review_params_count"] = len(review_params)
        result["blocked_params_count"] = len(blocked_params)
        return result

    # --- clearance_tb / creepage_tb: condition_type_mismatch ---
    if field_id in ("clearance_tb", "creepage_tb"):
        if best_blockers and "condition_type_mismatch" in best_blockers:
            result["selection_status"] = "blocked"
            result["selector_score"] = best_score
            result["selector_reason"] = "condition_type_mismatch_tt_vs_tb"
            result["selector_warnings"] = best_soft.copy()
            result["selected_param"] = best_param
            result["review_params"] = review_params
            result["blocked_params"] = blocked_params
            result["review_params_count"] = len(review_params)
            result["blocked_params_count"] = len(blocked_params)
            return result

    # --- part_number: from table candidate -> review_needed ---
    if field_id == "part_number":
        result["selection_status"] = "review_needed"
        result["selector_score"] = best_score
        result["selector_reason"] = "table_candidate_should_be_metadata_extraction"
        result["selector_warnings"] = best_soft.copy()
        result["selected_param"] = best_param
        result["review_params"] = review_params
        result["blocked_params"] = blocked_params
        result["review_params_count"] = len(review_params)
        result["blocked_params_count"] = len(blocked_params)
        return result

    # --- manufacturer: always missing ---
    if field_id == "manufacturer":
        result["selection_status"] = "missing"
        result["selector_reason"] = "should_be_from_pdf_metadata"
        result["selector_warnings"].append("metadata_extraction_needed")
        return result

    # =======================================================================
    # General classification
    # =======================================================================

    # Check if best param has dangerous blockers
    if best_blockers:
        result["selection_status"] = "blocked"
        result["selector_score"] = best_score
        result["selector_reason"] = f"dangerous_blockers: {'; '.join(best_blockers)}"
        result["selector_warnings"] = best_soft.copy()
        result["selected_param"] = best_param
        result["review_params"] = review_params
        result["blocked_params"] = blocked_params
        result["review_params_count"] = len(review_params)
        result["blocked_params_count"] = len(blocked_params)
        return result

    # Check if best param has value
    if not _has_value(best_param):
        result["selection_status"] = "blocked"
        result["selector_score"] = best_score
        result["selector_reason"] = "no_value_parsed"
        result["selector_warnings"] = best_soft.copy()
        result["selected_param"] = best_param
        result["review_params"] = review_params
        result["blocked_params"] = blocked_params
        result["review_params_count"] = len(review_params)
        result["blocked_params_count"] = len(blocked_params)
        return result

    # Check if best param passes basic checks
    parse_status = best_param.get("parse_status", "failed")
    parse_quality = best_param.get("parse_quality", "low")
    unit_sanity = best_param.get("unit_sanity_status", "missing")
    source_text = best_param.get("source_text", "")
    source_page = best_param.get("source_page", 0)

    if parse_status not in ("parsed", "partial"):
        result["selection_status"] = "review_needed"
        result["selector_score"] = best_score
        result["selector_reason"] = f"parse_status={parse_status} not clean enough for final"
        result["selector_warnings"] = best_soft.copy()
        result["selected_param"] = best_param
        result["review_params"] = review_params
        result["blocked_params"] = blocked_params
        result["review_params_count"] = len(review_params)
        result["blocked_params_count"] = len(blocked_params)
        return result

    if parse_quality == "low":
        result["selection_status"] = "review_needed"
        result["selector_score"] = best_score
        result["selector_reason"] = "parse_quality=low"
        result["selector_warnings"] = best_soft.copy()
        result["selected_param"] = best_param
        result["review_params"] = review_params
        result["blocked_params"] = blocked_params
        result["review_params_count"] = len(review_params)
        result["blocked_params_count"] = len(blocked_params)
        return result

    if unit_sanity in ("mismatch", "rejected"):
        result["selection_status"] = "review_needed"
        result["selector_score"] = best_score
        result["selector_reason"] = f"unit_sanity_status={unit_sanity}"
        result["selector_warnings"] = best_soft.copy()
        result["selected_param"] = best_param
        result["review_params"] = review_params
        result["blocked_params"] = blocked_params
        result["review_params_count"] = len(review_params)
        result["blocked_params_count"] = len(blocked_params)
        return result

    if not source_text:
        result["selection_status"] = "review_needed"
        result["selector_score"] = best_score
        result["selector_reason"] = "empty_source_text"
        result["selector_warnings"] = best_soft.copy()
        result["selected_param"] = best_param
        result["review_params"] = review_params
        result["blocked_params"] = blocked_params
        result["review_params_count"] = len(review_params)
        result["blocked_params_count"] = len(blocked_params)
        return result

    if source_page < 1:
        result["selection_status"] = "review_needed"
        result["selector_score"] = best_score
        result["selector_reason"] = "invalid_source_page"
        result["selector_warnings"] = best_soft.copy()
        result["selected_param"] = best_param
        result["review_params"] = review_params
        result["blocked_params"] = blocked_params
        result["review_params_count"] = len(review_params)
        result["blocked_params_count"] = len(blocked_params)
        return result

    # =======================================================================
    # Best param passes all basic checks
    # Score-based final vs review
    # =======================================================================
    if best_score >= 50 and not best_blockers:
        result["selection_status"] = "final_candidate"
        result["selector_score"] = best_score
        result["selector_reason"] = f"score={best_score} passes threshold, no dangerous blockers"
        result["selector_warnings"] = best_soft.copy()
        result["selected_param"] = best_param
        result["review_params"] = review_params[1:]  # Exclude best from review
        result["blocked_params"] = blocked_params
        result["review_params_count"] = len(review_params) - 1
        result["blocked_params_count"] = len(blocked_params)
    else:
        result["selection_status"] = "review_needed"
        result["selector_score"] = best_score
        reason_suffix = "; ".join(best_soft) if best_soft else "score below final threshold"
        result["selector_reason"] = f"score={best_score} ({reason_suffix})"
        result["selector_warnings"] = best_soft.copy()
        result["selected_param"] = best_param
        result["review_params"] = review_params
        result["blocked_params"] = blocked_params
        result["review_params_count"] = len(review_params)
        result["blocked_params_count"] = len(blocked_params)

    return result


# =============================================================================
# Main Selector Function
# =============================================================================

def _to_dict(p: Any) -> Dict[str, Any]:
    """Convert a RawExtractedParam dataclass or dict to a plain dict."""
    if isinstance(p, dict):
        return p
    # Assume dataclass with asdict method or __dict__
    if hasattr(p, "asdict"):
        return p.asdict()
    return vars(p)


def select_final_candidates(
    parsed_params: List[Any],
    target_fields: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Main entry point for Final Selector v0.
    
    Args:
        parsed_params: List of RawExtractedParam dataclass objects or dicts
        target_fields: List of field config dicts from target_fields.yaml
    
    Returns:
        Selection result dict with per-field selection status
    """
    # Build lookup - convert all to dicts
    by_field: Dict[str, List[Dict[str, Any]]] = {}
    for p in parsed_params:
        d = _to_dict(p)
        fid = d.get("field_id", "unknown")
        if fid not in by_field:
            by_field[fid] = []
        by_field[fid].append(d)

    results = {
        "field_count": len(target_fields),
        "final_candidate_count": 0,
        "review_needed_count": 0,
        "blocked_count": 0,
        "missing_count": 0,
        "fields": [],
    }

    for field_config in target_fields:
        fid = field_config["id"]
        params = by_field.get(fid, [])
        result = _classify_field(params, field_config)
        results["fields"].append(result)

        # Count by status
        status = result["selection_status"]
        if status == "final_candidate":
            results["final_candidate_count"] += 1
        elif status == "review_needed":
            results["review_needed_count"] += 1
        elif status == "blocked":
            results["blocked_count"] += 1
        elif status == "missing":
            results["missing_count"] += 1

    return results


# =============================================================================
# Selector Audit Report Generator
# =============================================================================

def generate_selector_audit(selection_result: Dict[str, Any]) -> str:
    """Generate selector_audit.md markdown report."""
    lines = []
    lines.append("# Final Selector Audit (Step 6)")
    lines.append("")
    lines.append("## 1. Overview")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total Target Fields | {selection_result['field_count']} |")
    lines.append(f"| **final_candidate** | **{selection_result['final_candidate_count']}** |")
    lines.append(f"| review_needed | {selection_result['review_needed_count']} |")
    lines.append(f"| blocked | {selection_result['blocked_count']} |")
    lines.append(f"| missing | {selection_result['missing_count']} |")
    lines.append("")

    # Separate fields by status
    final_fields = [f for f in selection_result["fields"] if f["selection_status"] == "final_candidate"]
    review_fields = [f for f in selection_result["fields"] if f["selection_status"] == "review_needed"]
    blocked_fields = [f for f in selection_result["fields"] if f["selection_status"] == "blocked"]
    missing_fields = [f for f in selection_result["fields"] if f["selection_status"] == "missing"]

    # =======================================================================
    # Section 2: Final Candidates
    # =======================================================================
    lines.append("## 2. Final Candidates")
    lines.append("")
    if final_fields:
        lines.append(f"| Field ID | Value | Unit | Score | Page | Reason |")
        lines.append(f"|----------|-------|------|-------|------|--------|")
        for f in final_fields:
            p = f["selected_param"]
            val_parts = []
            if p.get("min") is not None:
                val_parts.append(f"min={p['min']}")
            if p.get("typ") is not None:
                val_parts.append(f"typ={p['typ']}")
            if p.get("max") is not None:
                val_parts.append(f"max={p['max']}")
            if p.get("value") is not None:
                val_parts.append(f"val={p['value']}")
            val_str = ", ".join(val_parts) if val_parts else "-"
            unit = p.get("original_unit", "-")
            score = f["selector_score"]
            page = p.get("source_page", "-")
            reason = f["selector_reason"][:60]
            lines.append(f"| {f['field_id']} | {val_str} | {unit} | {score} | {page} | {reason} |")
        lines.append("")
    else:
        lines.append("*No final candidates.*")
        lines.append("")

    # =======================================================================
    # Section 3: Review Needed Fields
    # =======================================================================
    lines.append("## 3. Review Needed Fields")
    lines.append("")
    if review_fields:
        lines.append(f"| Field ID | Score | Reason | Warnings | Candidates |")
        lines.append(f"|----------|-------|--------|----------|------------|")
        for f in sorted(review_fields, key=lambda x: -x["selector_score"]):
            score = f["selector_score"]
            reason = f["selector_reason"][:50]
            warnings = ", ".join(f["selector_warnings"])[:60] if f["selector_warnings"] else "-"
            count = f["candidate_count"]
            lines.append(f"| {f['field_id']} | {score} | {reason} | {warnings} | {count} |")
        lines.append("")
    else:
        lines.append("*No review-needed fields.*")
        lines.append("")

    # =======================================================================
    # Section 4: Blocked Fields
    # =======================================================================
    lines.append("## 4. Blocked Fields")
    lines.append("")
    if blocked_fields:
        lines.append(f"| Field ID | Reason | Candidates |")
        lines.append(f"|----------|--------|------------|")
        for f in blocked_fields:
            reason = f["selector_reason"][:70]
            count = f["candidate_count"]
            lines.append(f"| {f['field_id']} | {reason} | {count} |")
        lines.append("")
    else:
        lines.append("*No blocked fields.*")
        lines.append("")

    # =======================================================================
    # Section 5: Missing Fields
    # =======================================================================
    lines.append("## 5. Missing Fields")
    lines.append("")
    if missing_fields:
        lines.append(f"| Field ID | Reason | Suggested Action |")
        lines.append(f"|----------|--------|------------------|")
        for f in missing_fields:
            reason = f["selector_reason"]
            action = "metadata/page_text extraction" if f["field_id"] in ("manufacturer", "part_number") else "parser_fix_or_missing_in_pdf"
            lines.append(f"| {f['field_id']} | {reason} | {action} |")
        lines.append("")
    else:
        lines.append("*No missing fields.*")
        lines.append("")

    # =======================================================================
    # Section 6: vgs_th Selection Check
    # =======================================================================
    lines.append("## 6. vgs_th Selection Check")
    lines.append("")
    vgs_th_fields = [f for f in selection_result["fields"] if f["field_id"] == "vgs_th"]
    if vgs_th_fields:
        vf = vgs_th_fields[0]
        p = vf["selected_param"]
        lines.append(f"**Selection Status**: {vf['selection_status']}")
        lines.append(f"**Selector Score**: {vf['selector_score']}")
        lines.append(f"**Selector Reason**: {vf['selector_reason']}")
        lines.append("")
        lines.append(f"| Property | Value |")
        lines.append(f"|----------|-------|")
        lines.append(f"| min | {p.get('min', '-')} |")
        lines.append(f"| max | {p.get('max', '-')} |")
        lines.append(f"| value | {p.get('value', '-')} |")
        lines.append(f"| original_unit | {p.get('original_unit', '-')} |")
        lines.append(f"| source_page | {p.get('source_page', '-')} |")
        lines.append(f"| row_index | {p.get('row_index', '-')} |")
        lines.append(f"| source_text | {p.get('source_text', '-')[:100]} |")
        lines.append(f"| parse_status | {p.get('parse_status', '-')} |")
        lines.append(f"| parse_quality | {p.get('parse_quality', '-')} |")
        lines.append(f"| unit_sanity_status | {p.get('unit_sanity_status', '-')} |")
        lines.append(f"| unit_source | {p.get('unit_source', '-')} |")
        lines.append(f"| review_reason | {p.get('review_reason', '-')} |")
        lines.append(f"| Warnings | {', '.join(vf['selector_warnings']) or '-'} |")
        lines.append("")
        
        # Check if this is the clean candidate
        is_clean = (
            p.get("min") == 2.0 and
            p.get("max") == 4.0 and
            p.get("original_unit") == "V" and
            "figure_caption" not in (p.get("review_reason") or "")
        )
        lines.append(f"**Is Clean vgs_th Candidate (min=2.0, max=4.0, unit=V, no figure)**: {'YES ✅' if is_clean else 'NO ❌'}")
        lines.append("")
    else:
        lines.append("*No vgs_th field found.*")
        lines.append("")

    # =======================================================================
    # Section 7: High-risk Rating Fields
    # =======================================================================
    lines.append("## 7. High-risk Rating Fields")
    lines.append("")
    rating_fields = ["current_rating", "voltage_rating"]
    for rfid in rating_fields:
        rfields = [f for f in selection_result["fields"] if f["field_id"] == rfid]
        if rfields:
            rf = rfields[0]
            lines.append(f"### {rfid}")
            lines.append("")
            lines.append(f"**Selection Status**: {rf['selection_status']}")
            lines.append(f"**Selector Score**: {rf['selector_score']}")
            lines.append(f"**Selector Reason**: {rf['selector_reason']}")
            p = rf["selected_param"]
            if p:
                val_parts = []
                if p.get("value") is not None:
                    val_parts.append(f"value={p['value']}")
                if p.get("original_unit"):
                    val_parts.append(f"unit={p['original_unit']}")
                lines.append(f"**Best Candidate**: {', '.join(val_parts) if val_parts else 'N/A'}")
                lines.append(f"**Candidate Count**: {rf['candidate_count']}")
                lines.append(f"**Review Params**: {rf['review_params_count']}")
                lines.append(f"**Blocked Params**: {rf['blocked_params_count']}")
            lines.append("")
            lines.append(f"**Why not in Final**: High-risk field with ambiguous_rating_row or wrong_dimension issues. Defaulted to review_needed per v1 rules.")
            lines.append("")

    return "\n".join(lines)


def save_selection_json(selection_result: Dict[str, Any], path: str) -> None:
    """Save selection result to JSON (with param dicts)."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(selection_result, f, ensure_ascii=False, indent=2)
