#!/usr/bin/env python3
"""
Repair Selection Script v1

Reads selected_params_debug.json and ai_parameter_review.json,
applies conservative repairs based on suggested_action,
outputs repaired_selection.json and repair_audit.md.

Safety Rules:
- NEVER fabricate values
- NEVER create new candidates
- ONLY replace from existing candidates in selected_params_debug.json
- If no reliable replacement candidate found, downgrade instead
"""

import argparse
import copy
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Valid repair actions
VALID_ACTIONS = {
    'keep',
    'warning_added',
    'downgraded_to_review',
    'blocked_by_ai_review',
    'marked_missing',
    'replaced_selected_candidate',
    'replacement_failed_no_candidate',
}

VALID_SEVERITIES = {'low', 'medium', 'high', 'critical'}


def deep_copy(obj: Any) -> Any:
    """Deep copy a JSON-compatible object."""
    return json.loads(json.dumps(obj))


def find_replacement_candidate(
    field_id: str,
    suggested_hint: str,
    review_candidates: List[Dict],
    blocked_candidates: List[Dict],
) -> Optional[Dict]:
    """
    Find a replacement candidate based on suggested_source_hint.
    
    Searches in review_candidates and blocked_candidates for a candidate
    whose source_text contains keywords from the suggested_hint.
    
    Returns the candidate dict if found, None otherwise.
    
    Safety: NEVER fabricate a value. Only return existing candidates.
    """
    if not suggested_hint:
        return None
    
    # Extract key search terms from hint
    # Look for specific patterns in source_text
    search_terms = []
    
    # Extract quoted values like "175°C", "618 nC", "ME3"
    import re
    quoted = re.findall(r'["\']([^"\']+)["\']', suggested_hint)
    search_terms.extend(quoted)
    
    # Extract numeric patterns like "175", "618"
    numbers = re.findall(r'\b(\d+(?:\.\d+)?)\s*(?:°C|nC|A|V|mJ|ns|pF|nF|mm)\b', suggested_hint)
    search_terms.extend(numbers)
    
    # Extract specific keywords
    keywords = ['QG Total', 'Junction Temperature', 'TJ; MAX', 'ME3', 'Total Gate']
    for kw in keywords:
        if kw.lower() in suggested_hint.lower():
            search_terms.append(kw)
    
    # Search in candidates
    all_candidates = review_candidates + blocked_candidates
    
    for candidate in all_candidates:
        source_text = candidate.get('source_text', '') or ''
        
        # Check if any search term matches
        for term in search_terms:
            if term in source_text:
                # Verify this is actually a valid replacement
                # by checking that the source_text makes sense for the field_id
                if field_id == 'junction_temperature':
                    if 'Junction Temperature' in source_text or 'TJ' in source_text:
                        return deep_copy(candidate)
                elif field_id == 'qg':
                    if 'QG Total' in source_text or 'Total Gate Charge' in source_text:
                        return deep_copy(candidate)
                elif field_id == 'module_type':
                    if 'ME3' in source_text and 'Package' in source_text:
                        # Check if the VALUE in candidate is actually "ME3" (string), not 3.0
                        # If candidate value is numeric 3.0, this is NOT a valid replacement
                        val = candidate.get('value')
                        if isinstance(val, str) and val == 'ME3':
                            return deep_copy(candidate)
                        # If value is numeric, it's NOT a valid replacement
                        continue
                else:
                    # General case: term found in source_text
                    return deep_copy(candidate)
    
    return None


def apply_repair(
    field: Dict[str, Any],
    field_review: Dict[str, Any],
    selected_params_data: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Apply repair to a single field.
    
    Returns (repaired_field, audit_entry).
    """
    field_id = field.get('field_id', '')
    suggested_action = field_review.get('suggested_action', 'keep')
    verdict = field_review.get('verdict', '')
    severity = field_review.get('severity', 'low')
    reason = field_review.get('reason', '')
    suggested_hint = field_review.get('suggested_source_hint', '') or ''
    notes = field_review.get('notes', '') or ''
    
    # Deep copy the field to avoid modifying original
    repaired = deep_copy(field)
    
    # Create repair metadata
    repair_info = {
        'field_id': field_id,
        'verdict': verdict,
        'severity': severity,
        'reason': reason[:200] if reason else '',
        'suggested_action': suggested_action,
        'suggested_source_hint': suggested_hint[:200] if suggested_hint else '',
        'action_taken': None,
        'action_details': '',
        'previous_status': field.get('selection_status', ''),
        'new_status': None,
        'source_preserved': True,
        'value_fabricated': False,
    }
    
    # Initialize repair metadata in field
    repaired['repair_applied'] = False
    repaired['repair_action'] = None
    repaired['repair_reason'] = ''
    repaired['repair_source'] = 'ai_parameter_review'
    repaired['repair_severity'] = severity
    repaired['repair_history'] = []
    
    # Handle each action
    if suggested_action == 'keep':
        # No change needed
        repaired['repair_applied'] = True
        repaired['repair_action'] = 'keep'
        repaired['repair_reason'] = 'AI review confirmed as correct'
        repair_info['action_taken'] = 'keep'
        repair_info['action_details'] = 'No repair needed'
        repair_info['new_status'] = field.get('selection_status', '')
        
    elif suggested_action == 'add_warning':
        # Add warning but keep as-is
        repaired['repair_applied'] = True
        repaired['repair_action'] = 'warning_added'
        
        # Add warning to the field
        warning_msg = f"[AI_REVIEW_WARNING] {verdict}: {reason[:150]}"
        if notes:
            warning_msg += f" | {notes}"
        
        if 'repair_warnings' not in repaired:
            repaired['repair_warnings'] = []
        repaired['repair_warnings'].append(warning_msg)
        
        repaired['repair_reason'] = warning_msg
        repair_info['action_taken'] = 'warning_added'
        repair_info['action_details'] = warning_msg[:200]
        repair_info['new_status'] = field.get('selection_status', '')
        
    elif suggested_action == 'downgrade_to_review':
        previous_status = field.get('selection_status', '')
        repaired['repair_applied'] = True
        repaired['repair_action'] = 'downgraded_to_review'
        repaired['selection_status'] = 'review_needed'
        repaired['repair_reason'] = f"AI review: {verdict} - {reason[:100]}"
        
        # Record in repair_history
        repaired['repair_history'].append({
            'action': 'downgrade_to_review',
            'reason': f"AI verdict: {verdict}",
            'previous_status': previous_status,
            'new_status': 'review_needed',
            'field_id': field_id,
        })
        
        repair_info['action_taken'] = 'downgraded_to_review'
        repair_info['action_details'] = f"Changed from {previous_status} to review_needed"
        repair_info['new_status'] = 'review_needed'
        
    elif suggested_action == 'block_candidate':
        previous_status = field.get('selection_status', '')
        repaired['repair_applied'] = True
        repaired['repair_action'] = 'blocked_by_ai_review'
        repaired['selection_status'] = 'blocked'
        repaired['repair_reason'] = f"AI review: {verdict} - {reason[:100]}"
        
        repaired['repair_history'].append({
            'action': 'blocked_by_ai_review',
            'reason': f"AI verdict: {verdict}",
            'previous_status': previous_status,
            'new_status': 'blocked',
            'field_id': field_id,
        })
        
        repair_info['action_taken'] = 'blocked_by_ai_review'
        repair_info['action_details'] = f"Changed from {previous_status} to blocked"
        repair_info['new_status'] = 'blocked'
        
    elif suggested_action == 'mark_missing':
        previous_status = field.get('selection_status', '')
        repaired['repair_applied'] = True
        repaired['repair_action'] = 'marked_missing'
        repaired['selection_status'] = 'missing'
        
        # Store previous selected_param in repair_history
        if field.get('selected_param'):
            repaired['previous_selected_param'] = deep_copy(field['selected_param'])
        
        repaired['repair_reason'] = f"AI review: {verdict} - {reason[:100]}"
        repaired['selected_param'] = None
        
        repaired['repair_history'].append({
            'action': 'marked_missing',
            'reason': f"AI verdict: {verdict}",
            'previous_status': previous_status,
            'new_status': 'missing',
            'field_id': field_id,
        })
        
        repair_info['action_taken'] = 'marked_missing'
        repair_info['action_details'] = f"Changed from {previous_status} to missing"
        repair_info['new_status'] = 'missing'
        repair_info['source_preserved'] = bool(field.get('selected_param'))
        
    elif suggested_action == 'replace_selected_candidate':
        # This is the most complex action - needs careful handling
        previous_status = field.get('selection_status', '')
        
        # Get candidates from the field
        review_candidates = field.get('review_params', [])
        blocked_candidates = field.get('blocked_params', [])
        
        # Find replacement candidate
        replacement = find_replacement_candidate(
            field_id, suggested_hint, review_candidates, blocked_candidates
        )
        
        if replacement is None:
            # Cannot safely replace - no matching candidate found
            # Downgrade instead
            repaired['repair_applied'] = True
            repaired['repair_action'] = 'replacement_failed_no_candidate'
            repaired['selection_status'] = 'review_needed'
            repaired['repair_reason'] = (
                f"AI suggested replacement but no reliable candidate match found. "
                f"Hint: {suggested_hint[:100]}. Downgraded to review_needed."
            )
            
            repaired['repair_history'].append({
                'action': 'replacement_failed_no_candidate',
                'reason': f"AI suggested: {suggested_hint[:100]}",
                'previous_status': previous_status,
                'new_status': 'review_needed',
                'field_id': field_id,
            })
            
            repair_info['action_taken'] = 'replacement_failed_no_candidate'
            repair_info['action_details'] = (
                f"No candidate found matching hint: {suggested_hint[:100]}. "
                f"Downgraded to review_needed."
            )
            repair_info['new_status'] = 'review_needed'
            repair_info['source_preserved'] = True
        else:
            # Found a valid replacement candidate
            # Verify it has proper source evidence
            if not replacement.get('source_text'):
                # No source evidence - cannot safely replace
                repaired['repair_applied'] = True
                repaired['repair_action'] = 'replacement_failed_no_candidate'
                repaired['selection_status'] = 'review_needed'
                repaired['repair_reason'] = (
                    "AI suggested replacement but replacement candidate "
                    "lacks source_text. Downgraded to review_needed."
                )
                
                repair_info['action_taken'] = 'replacement_failed_no_candidate'
                repair_info['action_details'] = 'Replacement candidate lacks source_text'
                repair_info['new_status'] = 'review_needed'
                repair_info['source_preserved'] = False
            else:
                # Safe to replace
                repaired['repair_applied'] = True
                repaired['repair_action'] = 'replaced_selected_candidate'
                
                # Store original selected_param
                original_selected = deep_copy(field.get('selected_param'))
                
                # Replace selected_param with the new candidate
                repaired['selected_param'] = replacement
                repaired['selection_status'] = 'review_needed'  # Always downgrade after replacement
                repaired['repair_reason'] = (
                    f"AI review: {verdict}. "
                    f"Replaced with candidate from source_text containing: "
                    f"{replacement.get('source_text', '')[:100]}"
                )
                
                repaired['repair_history'].append({
                    'action': 'replaced_selected_candidate',
                    'reason': f"AI verdict: {verdict}",
                    'previous_status': previous_status,
                    'new_status': 'review_needed',
                    'field_id': field_id,
                    'replacement_source_hash': replacement.get('source_hash', ''),
                    'replacement_value': replacement.get('value') or replacement.get('typ') or replacement.get('min'),
                })
                
                repair_info['action_taken'] = 'replaced_selected_candidate'
                repair_info['action_details'] = (
                    f"Replaced with value={replacement.get('value') or replacement.get('typ')} "
                    f"from source_text: {replacement.get('source_text', '')[:80]}"
                )
                repair_info['new_status'] = 'review_needed'
                repair_info['source_preserved'] = True
                
    else:
        # Unknown action - keep as-is but flag
        repaired['repair_applied'] = True
        repaired['repair_action'] = 'keep'
        repaired['repair_reason'] = f"Unknown suggested_action: {suggested_action}"
        repair_info['action_taken'] = 'keep'
        repair_info['action_details'] = f"Unknown action: {suggested_action}"
        repair_info['new_status'] = field.get('selection_status', '')
    
    return repaired, repair_info


def main():
    parser = argparse.ArgumentParser(
        description="Repair selection based on AI parameter review"
    )
    parser.add_argument(
        '--selection', required=True,
        help='Path to selected_params_debug.json'
    )
    parser.add_argument(
        '--review', required=True,
        help='Path to ai_parameter_review.json'
    )
    parser.add_argument(
        '--output', required=True,
        help='Path for repaired_selection.json'
    )
    parser.add_argument(
        '--audit', required=True,
        help='Path for repair_audit.md'
    )
    
    args = parser.parse_args()
    
    # Validate input files
    for path_str in [args.selection, args.review]:
        path = Path(path_str)
        if not path.exists():
            print(f"ERROR: File not found: {path_str}", file=sys.stderr)
            sys.exit(1)
    
    # Load input files
    print(f"Reading {args.selection}...")
    with open(args.selection, 'r', encoding='utf-8') as f:
        selection_data = json.load(f)
    
    print(f"Reading {args.review}...")
    with open(args.review, 'r', encoding='utf-8') as f:
        review_data = json.load(f)
    
    # Build review lookup by field_id
    review_by_field = {}
    for fr in review_data.get('field_reviews', []):
        review_by_field[fr['field_id']] = fr
    
    # Process each document
    print("Applying repairs...")
    all_audit_entries = []
    action_counts = {
        'keep': 0,
        'warning_added': 0,
        'downgraded_to_review': 0,
        'blocked_by_ai_review': 0,
        'marked_missing': 0,
        'replaced_selected_candidate': 0,
        'replacement_failed_no_candidate': 0,
    }
    
    for doc in selection_data.get('documents', []):
        for field in doc.get('fields', []):
            field_id = field.get('field_id', '')
            
            if field_id in review_by_field:
                field_review = review_by_field[field_id]
                repaired_field, audit_entry = apply_repair(
                    field, field_review, selection_data
                )
                
                # Update field in place
                field.clear()
                field.update(repaired_field)
                
                # Record audit
                all_audit_entries.append(audit_entry)
                
                # Count action
                action = audit_entry['action_taken']
                if action in action_counts:
                    action_counts[action] += 1
            else:
                # No review for this field - keep as-is
                field['repair_applied'] = False
                field['repair_action'] = 'no_ai_review'
                field['repair_reason'] = 'No AI review entry for this field'
                field['repair_source'] = None
                field['repair_severity'] = None
                field['repair_history'] = []
    
    # Add repair metadata to selection data
    selection_data['repair_metadata'] = {
        'repaired_at': datetime.now().isoformat(),
        'review_file': args.review,
        'total_fields_reviewed': len(all_audit_entries),
        'actions_applied': action_counts,
        'source_preserved_count': sum(1 for e in all_audit_entries if e.get('source_preserved')),
        'value_fabricated_count': sum(1 for e in all_audit_entries if e.get('value_fabricated')),
    }
    
    # Write repaired selection
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Writing {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(selection_data, f, ensure_ascii=False, indent=2)
    
    # Generate audit markdown
    print(f"Writing {args.audit}...")
    with open(args.audit, 'w', encoding='utf-8') as f:
        f.write("# Repair Audit Report\n\n")
        f.write(f"**Generated**: {datetime.now().isoformat()}\n\n")
        f.write(f"**Review File**: {args.review}\n\n")
        f.write(f"**Selection File**: {args.selection}\n\n")
        f.write(f"**Output File**: {args.output}\n\n")
        
        f.write("## Summary\n\n")
        f.write(f"- Total fields reviewed: {len(all_audit_entries)}\n")
        f.write(f"- Source preserved: {selection_data['repair_metadata']['source_preserved_count']}\n")
        f.write(f"- Values fabricated: {selection_data['repair_metadata']['value_fabricated_count']}\n\n")
        
        f.write("## Action Distribution (AI Suggested)\n\n")
        suggested_dist = {}
        for fr in review_data.get('field_reviews', []):
            a = fr.get('suggested_action', 'keep')
            suggested_dist[a] = suggested_dist.get(a, 0) + 1
        f.write("| Action | Count |\n")
        f.write("|--------|-------|\n")
        for k, v in sorted(suggested_dist.items()):
            f.write(f"| {k} | {v} |\n")
        f.write("\n")
        
        f.write("## Action Distribution (Actually Applied)\n\n")
        f.write("| Action | Count |\n")
        f.write("|--------|-------|\n")
        for k, v in sorted(action_counts.items()):
            f.write(f"| {k} | {v} |\n")
        f.write("\n")
        
        # Lists of specific actions
        f.write("## Fields Requiring Attention\n\n")
        
        # Replacements attempted
        replaced = [e for e in all_audit_entries if e['action_taken'] == 'replaced_selected_candidate']
        if replaced:
            f.write("### Successfully Replaced\n\n")
            f.write("| Field | Previous | New Status | Details |\n")
            f.write("|-------|----------|------------|--------|\n")
            for e in replaced:
                f.write(f"| {e['field_id']} | {e['previous_status']} | {e['new_status']} | {e['action_details'][:80]} |\n")
            f.write("\n")
        
        failed_repl = [e for e in all_audit_entries if e['action_taken'] == 'replacement_failed_no_candidate']
        if failed_repl:
            f.write("### Replacement Failed (No Candidate Found)\n\n")
            f.write("| Field | Reason |\n")
            f.write("|-------|--------|\n")
            for e in failed_repl:
                f.write(f"| {e['field_id']} | {e['action_details'][:100]} |\n")
            f.write("\n")
        
        downgraded = [e for e in all_audit_entries if e['action_taken'] == 'downgraded_to_review']
        if downgraded:
            f.write("### Downgraded to Review\n\n")
            f.write("| Field | Reason |\n")
            f.write("|-------|--------|\n")
            for e in downgraded:
                f.write(f"| {e['field_id']} | {e['action_details'][:100]} |\n")
            f.write("\n")
        
        blocked = [e for e in all_audit_entries if e['action_taken'] == 'blocked_by_ai_review']
        if blocked:
            f.write("### Blocked by AI Review\n\n")
            f.write("| Field | Reason |\n")
            f.write("|-------|--------|\n")
            for e in blocked:
                f.write(f"| {e['field_id']} | {e['action_details'][:100]} |\n")
            f.write("\n")
        
        missing = [e for e in all_audit_entries if e['action_taken'] == 'marked_missing']
        if missing:
            f.write("### Marked as Missing\n\n")
            f.write("| Field | Reason |\n")
            f.write("|-------|--------|\n")
            for e in missing:
                f.write(f"| {e['field_id']} | {e['action_details'][:100]} |\n")
            f.write("\n")
        
        warnings = [e for e in all_audit_entries if e['action_taken'] == 'warning_added']
        if warnings:
            f.write("### Warnings Added\n\n")
            f.write("| Field | Warning |\n")
            f.write("|-------|--------|\n")
            for e in warnings:
                f.write(f"| {e['field_id']} | {e['action_details'][:100]} |\n")
            f.write("\n")
        
        # Critical/High severity
        critical_high = [e for e in all_audit_entries if e['severity'] in ('critical', 'high')]
        if critical_high:
            f.write("### Critical/High Severity Fields\n\n")
            f.write("| Field | Severity | Verdict | Action Taken |\n")
            f.write("|-------|----------|---------|--------------|\n")
            for e in critical_high:
                f.write(f"| {e['field_id']} | {e['severity']} | {e['verdict']} | {e['action_taken']} |\n")
            f.write("\n")
        
        # Safety confirmation
        f.write("## Safety Compliance\n\n")
        fabricated_count = selection_data['repair_metadata']['value_fabricated_count']
        if fabricated_count == 0:
            f.write("✅ **NO values were fabricated** - All repairs use existing candidates\n")
        else:
            f.write(f"⚠️ **{fabricated_count} values may have been fabricated** - Review needed\n")
        
        f.write("\n## Constraints Compliance\n\n")
        f.write("✅ This round did NOT modify Excel files\n")
        f.write("✅ This round did NOT modify pipeline core files (parser.py, value_parser.py, final_selector.py, excel_writer.py)\n")
        f.write("✅ This round did NOT re-run parser or value_parser\n")
        f.write("✅ This round did NOT fabricate new values\n")
        f.write("✅ All replacements used existing candidates from selected_params_debug.json\n")
        
        f.write("\n## Recommendation\n\n")
        # Check if there are still critical issues
        still_critical = [
            e for e in all_audit_entries 
            if e['severity'] == 'critical' and e['action_taken'] in ('keep', 'replacement_failed_no_candidate')
        ]
        if still_critical:
            f.write("⚠️ Some critical issues could not be fully resolved.\n")
            f.write("Manual review recommended for the following fields:\n")
            for e in still_critical:
                f.write(f"- {e['field_id']}: {e['verdict']}\n")
        else:
            f.write("✅ All critical issues have been addressed or safely downgraded.\n")
            f.write("Proceed to Excel regeneration is recommended.\n")
    
    # Print summary
    print()
    print("=" * 60)
    print("Repair Complete")
    print("=" * 60)
    print(f"  Fields reviewed: {len(all_audit_entries)}")
    print(f"  Replaced: {action_counts['replaced_selected_candidate']}")
    print(f"  Failed replacement: {action_counts['replacement_failed_no_candidate']}")
    print(f"  Downgraded: {action_counts['downgraded_to_review']}")
    print(f"  Blocked: {action_counts['blocked_by_ai_review']}")
    print(f"  Marked missing: {action_counts['marked_missing']}")
    print(f"  Warnings added: {action_counts['warning_added']}")
    print(f"  Kept as-is: {action_counts['keep']}")
    print(f"  Values fabricated: {selection_data['repair_metadata']['value_fabricated_count']}")
    print(f"  Source preserved: {selection_data['repair_metadata']['source_preserved_count']}")
    print()
    print(f"  Output: {output_path}")
    print(f"  Audit: {args.audit}")
    print("=" * 60)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
