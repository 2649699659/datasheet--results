"""
Final Selector v1 - Candidate Selection for Datasheet Extraction

Selects best candidate per field_id from parsed params and classifies as:
- final_candidate: Clean enough for Final Comparison
- review_needed: Has values but needs human review
- blocked: Dangerous/unusable candidates
- missing: No candidates found

Does NOT generate Excel. Pure selection logic.
"""

import json
import enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import is_dataclass, asdict


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

# Unknown document marker
UNKNOWN_DOCUMENT_ID = "unknown_document"


# =============================================================================
# JSON Serialization Helpers
# =============================================================================

def json_safe(obj: Any) -> Any:
    """
    Recursively convert an object to be JSON-serializable.
    Handles: Enum -> .value, Path -> str, dataclass -> dict,
             list/tuple -> list, dict -> dict.
    """
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, enum.Enum):
        return obj.value
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (list, tuple)):
        return [json_safe(item) for item in obj]
    if isinstance(obj, dict):
        return {k: json_safe(v) for k, v in obj.items()}
    if is_dataclass(obj):
        return json_safe(asdict(obj))
    # Fallback: try str
    try:
        return str(obj)
    except Exception:
        return repr(obj)


def _to_dict(p: Any) -> Dict[str, Any]:
    """
    Convert a RawExtractedParam dataclass or dict to a plain dict.
    
    Priority:
    1. Already a dict -> return as-is
    2. Has to_dict() method -> use it (RawExtractedParam.to_dict() handles Enums)
    3. Dataclass -> use dataclasses.asdict()
    4. Fallback -> vars()
    """
    if isinstance(p, dict):
        return p
    if hasattr(p, "to_dict"):
        return p.to_dict()
    if is_dataclass(p):
        return asdict(p)
    return vars(p)


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
    params: List[Dict[str, Any]],
    field_config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Classify a single field from its candidates (all params already converted to dicts).
    
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
# Document-level classification
# =============================================================================

def _classify_document(
    doc_params: Dict[str, List[Dict[str, Any]]],
    doc_info: Dict[str, str],
    target_fields: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Classify all fields for one document.
    
    Args:
        doc_params: {field_id: [param_dicts]} for this document
        doc_info: {document_id, file_name, pdf_stem, pdf_path}
        target_fields: List of field config dicts
    
    Returns:
        Document result dict with fields list
    """
    doc_result = {
        "document_id": doc_info.get("document_id", UNKNOWN_DOCUMENT_ID),
        "file_name": doc_info.get("file_name", "unknown"),
        "pdf_stem": doc_info.get("pdf_stem", "unknown"),
        "pdf_path": doc_info.get("pdf_path", ""),
        "field_count": len(target_fields),
        "final_candidate_count": 0,
        "review_needed_count": 0,
        "blocked_count": 0,
        "missing_count": 0,
        "fields": [],
    }

    for field_config in target_fields:
        fid = field_config["id"]
        params = doc_params.get(fid, [])
        field_result = _classify_field(params, field_config)
        doc_result["fields"].append(field_result)

        status = field_result["selection_status"]
        if status == "final_candidate":
            doc_result["final_candidate_count"] += 1
        elif status == "review_needed":
            doc_result["review_needed_count"] += 1
        elif status == "blocked":
            doc_result["blocked_count"] += 1
        elif status == "missing":
            doc_result["missing_count"] += 1

    return doc_result


# =============================================================================
# Main Selector Function
# =============================================================================

def select_final_candidates(
    parsed_params: List[Any],
    target_fields: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Main entry point for Final Selector v1 (document-based).
    
    Args:
        parsed_params: List of RawExtractedParam dataclass objects or dicts
        target_fields: List of field config dicts from target_fields.yaml
    
    Returns:
        Document-based selection result dict:
        {
          "document_count": N,
          "field_count": 30,
          "total_final_candidate_count": 0,
          "total_review_needed_count": 0,
          "total_blocked_count": 0,
          "total_missing_count": 0,
          "documents": [
            {
              "document_id": "...",
              "file_name": "...",
              "pdf_stem": "...",
              "pdf_path": "...",
              "field_count": 30,
              "final_candidate_count": 0,
              "review_needed_count": 0,
              "blocked_count": 0,
              "missing_count": 0,
              "fields": [{field_result}, ...]
            },
            ...
          ]
        }
    """
    # Group params by document_id, then by field_id
    # {document_id: {field_id: [param_dicts]}}
    by_doc: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

    for p in parsed_params:
        d = _to_dict(p)
        doc_id = d.get("document_id") or UNKNOWN_DOCUMENT_ID
        fid = d.get("field_id", "unknown")

        if doc_id not in by_doc:
            by_doc[doc_id] = {}
        if fid not in by_doc[doc_id]:
            by_doc[doc_id][fid] = []
        by_doc[doc_id][fid].append(d)

    # Build document info from first param of each document
    doc_infos: Dict[str, Dict[str, str]] = {}
    for doc_id in by_doc:
        # Find first param with non-empty doc info
        for fid, params in by_doc[doc_id].items():
            for p in params:
                doc_infos[doc_id] = {
                    "document_id": p.get("document_id") or UNKNOWN_DOCUMENT_ID,
                    "file_name": p.get("file_name") or "unknown",
                    "pdf_stem": p.get("pdf_stem") or "unknown",
                    "pdf_path": p.get("pdf_path") or "",
                }
                break
            break
        if doc_id not in doc_infos:
            doc_infos[doc_id] = {
                "document_id": doc_id,
                "file_name": "unknown",
                "pdf_stem": "unknown",
                "pdf_path": "",
            }

    # Classify each document
    results = {
        "document_count": len(by_doc),
        "field_count": len(target_fields),
        "total_final_candidate_count": 0,
        "total_review_needed_count": 0,
        "total_blocked_count": 0,
        "total_missing_count": 0,
        "documents": [],
    }

    for doc_id in sorted(by_doc.keys()):
        doc_result = _classify_document(
            by_doc[doc_id],
            doc_infos[doc_id],
            target_fields,
        )
        results["documents"].append(doc_result)
        results["total_final_candidate_count"] += doc_result["final_candidate_count"]
        results["total_review_needed_count"] += doc_result["review_needed_count"]
        results["total_blocked_count"] += doc_result["blocked_count"]
        results["total_missing_count"] += doc_result["missing_count"]

    return results


# =============================================================================
# Selector Audit Report Generator
# =============================================================================

def generate_selector_audit(selection_result: Dict[str, Any]) -> str:
    """Generate selector_audit.md markdown report (document-based)."""
    lines = []
    lines.append("# Final Selector Audit (Step 6.1)")
    lines.append("")
    lines.append("## 1. Overview")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| document_count | {selection_result['document_count']} |")
    lines.append(f"| field_count | {selection_result['field_count']} |")
    lines.append(f"| **total_final_candidate** | **{selection_result['total_final_candidate_count']}** |")
    lines.append(f"| total_review_needed | {selection_result['total_review_needed_count']} |")
    lines.append(f"| total_blocked | {selection_result['total_blocked_count']} |")
    lines.append(f"| total_missing | {selection_result['total_missing_count']} |")
    lines.append("")

    # =======================================================================
    # Section 2: Documents Summary
    # =======================================================================
    lines.append("## 2. Documents Summary")
    lines.append("")
    lines.append(f"| document_id | file_name | pdf_stem | final_candidate | review_needed | blocked | missing |")
    lines.append(f"|-------------|----------|---------|----------------|--------------|--------|--------|")
    for doc in selection_result["documents"]:
        lines.append(
            f"| {doc['document_id']} | {doc['file_name']} | {doc['pdf_stem']} | "
            f"{doc['final_candidate_count']} | {doc['review_needed_count']} | "
            f"{doc['blocked_count']} | {doc['missing_count']} |"
        )
    lines.append("")

    # =======================================================================
    # Section 3: Per-document Selection
    # =======================================================================
    lines.append("## 3. Per-document Selection")
    lines.append("")

    for doc in selection_result["documents"]:
        lines.append(f"### Document: {doc['file_name']}")
        lines.append("")
        lines.append(f"document_id: `{doc['document_id']}`  |  pdf_stem: `{doc['pdf_stem']}`")
        lines.append("")

        final_fields = [f for f in doc["fields"] if f["selection_status"] == "final_candidate"]
        review_fields = [f for f in doc["fields"] if f["selection_status"] == "review_needed"]
        blocked_fields = [f for f in doc["fields"] if f["selection_status"] == "blocked"]
        missing_fields = [f for f in doc["fields"] if f["selection_status"] == "missing"]

        # Final Candidates
        lines.append("#### Final Candidates")
        if final_fields:
            lines.append(f"| Field ID | Value | Unit | Score | Page | Reason |")
            lines.append(f"|----------|-------|------|-------|------|--------|")
            for f in final_fields:
                p = f["selected_param"]
                val_parts = []
                if p and p.get("min") is not None:
                    val_parts.append(f"min={p['min']}")
                if p and p.get("typ") is not None:
                    val_parts.append(f"typ={p['typ']}")
                if p and p.get("max") is not None:
                    val_parts.append(f"max={p['max']}")
                if p and p.get("value") is not None:
                    val_parts.append(f"val={p['value']}")
                val_str = ", ".join(val_parts) if val_parts else "-"
                unit = (p.get("original_unit", "-") if p else "-")
                score = f["selector_score"]
                page = (p.get("source_page", "-") if p else "-")
                reason = f["selector_reason"][:60]
                lines.append(f"| {f['field_id']} | {val_str} | {unit} | {score} | {page} | {reason} |")
            lines.append("")
        else:
            lines.append("*No final candidates.*")
            lines.append("")

        # Review Needed
        lines.append("#### Review Needed")
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

        # Blocked
        lines.append("#### Blocked")
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

        # Missing
        lines.append("#### Missing")
        if missing_fields:
            lines.append(f"| Field ID | Suggested Action |")
            lines.append(f"|----------|------------------|")
            for f in missing_fields:
                action = "metadata/page_text extraction" if f["field_id"] in ("manufacturer", "part_number") else "parser_fix_or_missing_in_pdf"
                lines.append(f"| {f['field_id']} | {action} |")
            lines.append("")
        else:
            lines.append("*No missing fields.*")
            lines.append("")

    # =======================================================================
    # Section 4: vgs_th Selection Check
    # =======================================================================
    lines.append("## 4. vgs_th Selection Check")
    lines.append("")
    for doc in selection_result["documents"]:
        vgs_th_fields = [f for f in doc["fields"] if f["field_id"] == "vgs_th"]
        if vgs_th_fields:
            vf = vgs_th_fields[0]
            p = vf["selected_param"]
            lines.append(f"**Document**: {doc['file_name']} (`{doc['document_id']}`)")
            lines.append(f"**Selection Status**: {vf['selection_status']}")
            lines.append(f"**Selector Score**: {vf['selector_score']}")
            lines.append(f"**Selector Reason**: {vf['selector_reason']}")
            lines.append("")
            if p:
                lines.append(f"| Property | Value |")
                lines.append(f"|----------|-------|")
                lines.append(f"| min | {p.get('min', '-')} |")
                lines.append(f"| max | {p.get('max', '-')} |")
                lines.append(f"| value | {p.get('value', '-')} |")
                lines.append(f"| original_unit | {p.get('original_unit', '-')} |")
                lines.append(f"| source_page | {p.get('source_page', '-')} |")
                lines.append(f"| source_text | {p.get('source_text', '-')[:100]} |")
                lines.append(f"| parse_status | {p.get('parse_status', '-')} |")
                lines.append(f"| parse_quality | {p.get('parse_quality', '-')} |")
                lines.append(f"| unit_sanity_status | {p.get('unit_sanity_status', '-')} |")
                lines.append("")
                is_clean = (
                    p.get("min") == 2.0 and
                    p.get("max") == 4.0 and
                    p.get("original_unit") == "V" and
                    "figure_caption" not in (p.get("review_reason") or "")
                )
                lines.append(f"**Is Clean vgs_th (min=2.0, max=4.0, unit=V, no figure)**: {'YES ✅' if is_clean else 'NO ❌'}")
            else:
                lines.append("*No vgs_th candidate selected.*")
            lines.append("")
        else:
            lines.append(f"**Document**: {doc['file_name']} — no vgs_th field found")
            lines.append("")

    # =======================================================================
    # Section 5: High-risk Rating Fields
    # =======================================================================
    lines.append("## 5. High-risk Rating Fields")
    lines.append("")
    rating_fields = ["current_rating", "voltage_rating"]
    for rfid in rating_fields:
        lines.append(f"### {rfid}")
        lines.append("")
        for doc in selection_result["documents"]:
            rf = next((f for f in doc["fields"] if f["field_id"] == rfid), None)
            if rf:
                p = rf["selected_param"]
                lines.append(f"**Document**: {doc['file_name']} (`{doc['document_id']}`)")
                lines.append(f"- Selection Status: {rf['selection_status']}")
                lines.append(f"- Selector Score: {rf['selector_score']}")
                lines.append(f"- Selector Reason: {rf['selector_reason']}")
                if p:
                    val_parts = []
                    if p.get("value") is not None:
                        val_parts.append(f"value={p['value']}")
                    if p.get("original_unit"):
                        val_parts.append(f"unit={p['original_unit']}")
                    lines.append(f"- Best Candidate: {', '.join(val_parts) if val_parts else 'N/A'}")
                    lines.append(f"- Candidate Count: {rf['candidate_count']}")
                lines.append(f"- Why not in Final: High-risk field. Defaulted to review_needed per v1 rules.")
                lines.append("")
            else:
                lines.append(f"**Document**: {doc['file_name']} — no {rfid} field found")
                lines.append("")

    return "\n".join(lines)


def save_selection_json(selection_result: Dict[str, Any], path: str) -> None:
    """Save selection result to JSON with full JSON-safety."""
    # Apply json_safe recursively to ensure Enum objects are converted
    safe_result = json_safe(selection_result)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(safe_result, f, ensure_ascii=False, indent=2)
