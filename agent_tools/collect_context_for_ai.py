#!/usr/bin/env python3
"""
Collect Context for AI Review

Reads selected_params_debug.json and raw_params_debug.json to generate
a compact AI review context JSON.

Usage:
    python3 agent_tools/collect_context_for_ai.py \
        --selection output/selected_params_debug.json \
        --params output/raw_params_debug.json \
        --candidates output/raw_candidates_debug.json \
        --fields config/target_fields.yaml \
        --output output/ai_review_context.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Constants
MAX_SOURCE_TEXT_LEN = 600
MAX_REVIEW_CANDIDATES = 5
MAX_BLOCKED_CANDIDATES = 3


def truncate_text(text: str, max_len: int = MAX_SOURCE_TEXT_LEN) -> str:
    """Truncate text to max_len characters."""
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def safe_get_value(obj: Any, key: str, default: Any = None) -> Any:
    """Safely get value from dict, return default if not found."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


def extract_param_info(param: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract relevant info from a param dict.
    Preserves: source_page, source_hash, field_id, unit, condition, review_reason.
    """
    if param is None:
        return None
    
    # Get value fields
    value_info = {}
    for key in ['value', 'min', 'typ', 'max']:
        val = param.get(key)
        value_info[key] = val
    
    # Get unit info
    unit_info = {
        'unit': param.get('unit', ''),
        'original_unit': param.get('original_unit', ''),
    }
    
    # Get source info
    source_info = {
        'source_page': param.get('source_page', 0),
        'table_index': param.get('table_index', -1),
        'row_index': param.get('row_index', -1),
        'source_text': truncate_text(param.get('source_text', '')),
        'source_hash': param.get('source_hash', ''),
    }
    
    # Get reason info
    reason_info = {
        'review_reason': param.get('review_reason', ''),
        'selector_reason': param.get('selector_reason', ''),
        'parse_status': param.get('parse_status', ''),
        'parse_quality': param.get('parse_quality', ''),
    }
    
    # Get condition info
    condition_info = {
        'condition': param.get('condition', ''),
    }
    
    # Combine all
    result = {**value_info, **unit_info, **source_info, **reason_info, **condition_info}
    
    # Remove None values for cleaner output
    return {k: v for k, v in result.items() if v is not None and v != ''}


def extract_field_info(
    field: Dict[str, Any],
    params_data: Dict[str, Any],
    candidates_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Extract field info for AI review context.
    
    Args:
        field: Field from selected_params_debug.json
        params_data: Full raw_params_debug.json data
        candidates_data: Full raw_candidates_debug.json data
    
    Returns:
        Field info dict for AI review context
    """
    field_id = field.get('field_id', '')
    document_id = field.get('document_id', '')
    label = field.get('label', '')
    selection_status = field.get('selection_status', '')
    preferred_value = field.get('preferred_value', '')
    
    # Get selected_param
    selected_param = field.get('selected_param')
    selected_param_info = extract_param_info(selected_param)
    
    # Get review_params (from selected_params_debug.json)
    review_params = field.get('review_params', [])
    review_candidates = []
    for rp in review_params[:MAX_REVIEW_CANDIDATES]:
        info = extract_param_info(rp)
        if info:
            review_candidates.append(info)
    
    # Get blocked_params (from selected_params_debug.json)
    blocked_params = field.get('blocked_params', [])
    blocked_candidates = []
    for bp in blocked_params[:MAX_BLOCKED_CANDIDATES]:
        info = extract_param_info(bp)
        if info:
            blocked_candidates.append(info)
    
    # Build result
    result = {
        'field_id': field_id,
        'label': label,
        'preferred_value': preferred_value,
        'selection_status': selection_status,
        'selected_param': selected_param_info,
        'review_candidates': review_candidates,
        'blocked_candidates': blocked_candidates,
    }
    
    return result


def build_review_context(
    selection_data: Dict[str, Any],
    params_data: Dict[str, Any],
    candidates_data: Dict[str, Any],
    fields_data: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Build the AI review context JSON.
    
    Args:
        selection_data: parsed selected_params_debug.json
        params_data: parsed raw_params_debug.json (optional, for future use)
        candidates_data: parsed raw_candidates_debug.json (optional, for future use)
        fields_data: parsed target_fields.yaml (optional, for target_unit lookup)
    
    Returns:
        AI review context dict
    """
    # Build fields_data lookup if provided
    target_unit_map = {}
    if fields_data:
        for f in fields_data:
            field_id = f.get('id', '')
            unit = f.get('unit', '')
            target_unit_map[field_id] = unit
    
    # Process each document
    documents_out = []
    for doc in selection_data.get('documents', []):
        document_id = doc.get('document_id', '')
        file_name = doc.get('file_name', '')
        pdf_stem = doc.get('pdf_stem', '')
        
        # Process each field
        fields_out = []
        for field in doc.get('fields', []):
            field_info = extract_field_info(field, params_data, candidates_data)
            
            # Add target_unit if available
            field_id = field_info.get('field_id', '')
            if field_id in target_unit_map:
                field_info['target_unit'] = target_unit_map[field_id]
            
            fields_out.append(field_info)
        
        doc_out = {
            'document_id': document_id,
            'file_name': file_name,
            'pdf_stem': pdf_stem,
            'fields': fields_out,
        }
        
        documents_out.append(doc_out)
    
    # Build output
    output = {
        'document_count': len(documents_out),
        'field_count': sum(len(d['fields']) for d in documents_out),
        'documents': documents_out,
    }
    
    return output


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Collect context for AI review of datasheet extraction results"
    )
    
    parser.add_argument(
        '--selection',
        required=True,
        help='Path to selected_params_debug.json'
    )
    parser.add_argument(
        '--params',
        required=True,
        help='Path to raw_params_debug.json'
    )
    parser.add_argument(
        '--candidates',
        required=True,
        help='Path to raw_candidates_debug.json'
    )
    parser.add_argument(
        '--fields',
        required=True,
        help='Path to target_fields.yaml'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Output path for ai_review_context.json'
    )
    
    args = parser.parse_args()
    
    # Validate input files exist
    for path_str in [args.selection, args.params, args.candidates, args.fields]:
        path = Path(path_str)
        if not path.exists():
            print(f"ERROR: File not found: {path_str}", file=sys.stderr)
            sys.exit(1)
    
    # Load JSON files
    print(f"Reading {args.selection}...")
    with open(args.selection, 'r', encoding='utf-8') as f:
        selection_data = json.load(f)
    
    print(f"Reading {args.params}...")
    with open(args.params, 'r', encoding='utf-8') as f:
        params_data = json.load(f)
    
    print(f"Reading {args.candidates}...")
    with open(args.candidates, 'r', encoding='utf-8') as f:
        candidates_data = json.load(f)
    
    # Load YAML fields (if available, as JSON)
    fields_data = None
    if args.fields.endswith('.yaml') or args.fields.endswith('.yml'):
        try:
            import yaml
            print(f"Reading {args.fields}...")
            with open(args.fields, 'r', encoding='utf-8') as f:
                fields_data = yaml.safe_load(f)
                # Handle both list and dict with 'fields' key
                if isinstance(fields_data, dict):
                    fields_data = fields_data.get('fields', [])
        except ImportError:
            print(f"WARNING: PyYAML not installed, cannot load {args.fields}", file=sys.stderr)
            fields_data = None
        except Exception as e:
            print(f"WARNING: Failed to load {args.fields}: {e}", file=sys.stderr)
            fields_data = None
    else:
        # Assume JSON
        try:
            print(f"Reading {args.fields}...")
            with open(args.fields, 'r', encoding='utf-8') as f:
                fields_data = json.load(f)
                if isinstance(fields_data, dict):
                    fields_data = fields_data.get('fields', [])
        except Exception as e:
            print(f"WARNING: Failed to load {args.fields}: {e}", file=sys.stderr)
            fields_data = None
    
    # Build review context
    print("Building AI review context...")
    review_context = build_review_context(
        selection_data,
        params_data,
        candidates_data,
        fields_data
    )
    
    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Writing {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(review_context, f, ensure_ascii=False, indent=2)
    
    # Print summary
    print()
    print("=" * 60)
    print("AI Review Context Generated")
    print("=" * 60)
    print(f"  Documents: {review_context['document_count']}")
    print(f"  Fields: {review_context['field_count']}")
    print(f"  Output: {output_path}")
    print()
    
    # Per-document summary
    for doc in review_context['documents']:
        print(f"  Document: {doc['file_name']} ({doc['document_id']})")
        final_count = sum(1 for f in doc['fields'] if f['selection_status'] == 'final_candidate')
        review_count = sum(1 for f in doc['fields'] if f['selection_status'] == 'review_needed')
        blocked_count = sum(1 for f in doc['fields'] if f['selection_status'] == 'blocked')
        missing_count = sum(1 for f in doc['fields'] if f['selection_status'] == 'missing')
        print(f"    final_candidate: {final_count}")
        print(f"    review_needed: {review_count}")
        print(f"    blocked: {blocked_count}")
        print(f"    missing: {missing_count}")
    
    print("=" * 60)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
