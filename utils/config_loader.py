"""
Configuration Loader for target_fields.yaml

Loads and validates the target fields configuration.

Functions:
    - load_target_fields(config_path) -> List[Dict]
    - validate_field(field) -> Tuple[bool, str]
    - get_field_by_id(fields, field_id) -> Optional[Dict]
    - get_all_aliases(fields) -> Dict[str, str]  # alias -> field_id
"""

import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any


REQUIRED_FIELD_KEYS = ["id", "label", "unit", "aliases", "preferred_value"]
OPTIONAL_FIELD_KEYS = ["condition_keywords", "notes"]

# Extended default fields (not in YAML, added by loader)
DEFAULT_CATEGORY = "uncategorized"
DEFAULT_APPLIES_TO = ["module", "discrete_mosfet", "die", "unknown"]
DEFAULT_PRIORITY = "medium"
DEFAULT_UNIT_CONVERSION = True

# Matching Policy Fields (Step 4.7)
DEFAULT_EXPECTED_SOURCES = ["table"]
DEFAULT_MATCH_STRATEGY = "normal"
DEFAULT_ALLOW_FUZZY = True
DEFAULT_REQUIRED_CONTEXT = []
DEFAULT_FORBIDDEN_CONTEXT = []


def load_yaml(yaml_path: str) -> Dict[str, Any]:
    """
    Load YAML file.
    
    Args:
        yaml_path: Path to YAML file
        
    Returns:
        Parsed YAML dict
    """
    with open(yaml_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_field(field: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate a single field definition.
    
    Args:
        field: Field dict
        
    Returns:
        (is_valid, error_message)
    """
    # Check required keys
    for key in REQUIRED_FIELD_KEYS:
        if key not in field:
            return False, f"Missing required key: {key}"
    
    # Check aliases is a list
    if not isinstance(field["aliases"], list):
        return False, f"Field '{field['id']}': aliases must be a list"
    
    # Check label is not empty
    if not field["label"] or not field["label"].strip():
        return False, f"Field '{field['id']}': label cannot be empty"
    
    # Set defaults for optional keys
    if "condition_keywords" not in field:
        field["condition_keywords"] = []
    if "notes" not in field:
        field["notes"] = ""
    
    # Set defaults for extended fields (not in YAML, added by loader)
    if "category" not in field:
        field["category"] = DEFAULT_CATEGORY
    if "applies_to" not in field:
        field["applies_to"] = DEFAULT_APPLIES_TO.copy()
    if "priority" not in field:
        field["priority"] = DEFAULT_PRIORITY
    if "unit_conversion" not in field:
        field["unit_conversion"] = DEFAULT_UNIT_CONVERSION
    
    # Set defaults for Matching Policy Fields (Step 4.7)
    if "expected_sources" not in field:
        field["expected_sources"] = DEFAULT_EXPECTED_SOURCES.copy()
    if "match_strategy" not in field:
        field["match_strategy"] = DEFAULT_MATCH_STRATEGY
    if "allow_fuzzy" not in field:
        field["allow_fuzzy"] = DEFAULT_ALLOW_FUZZY
    if "required_context" not in field:
        field["required_context"] = DEFAULT_REQUIRED_CONTEXT.copy()
    if "forbidden_context" not in field:
        field["forbidden_context"] = DEFAULT_FORBIDDEN_CONTEXT.copy()
    
    # Special field-specific matching policy overrides (Step 4.7)
    field_id = field["id"]
    if field_id == "manufacturer":
        field["expected_sources"] = ["metadata", "page_text"]
        field["match_strategy"] = "metadata_text"
        field["allow_fuzzy"] = False
    elif field_id == "part_number":
        field["expected_sources"] = ["metadata", "page_text", "table"]
        field["match_strategy"] = "normal"
        field["allow_fuzzy"] = True
    elif field_id == "current_rating":
        field["expected_sources"] = ["title", "page_text", "table"]
        field["match_strategy"] = "strict_rating"
        field["allow_fuzzy"] = False
    elif field_id == "voltage_rating":
        field["expected_sources"] = ["title", "page_text", "table"]
        field["match_strategy"] = "strict_rating"
        field["allow_fuzzy"] = False
    
    return True, ""


def validate_all_fields(fields: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """
    Validate all fields and check for duplicates.
    
    Args:
        fields: List of field dicts
        
    Returns:
        (all_valid, list_of_errors)
    """
    errors = []
    seen_ids = set()
    seen_labels = set()
    
    for field in fields:
        # Validate individual field
        is_valid, error = validate_field(field)
        if not is_valid:
            errors.append(error)
            continue
        
        # Check for duplicate id
        field_id = field["id"]
        if field_id in seen_ids:
            errors.append(f"Duplicate field id: '{field_id}'")
        seen_ids.add(field_id)
        
        # Check for duplicate label
        label = field["label"].strip()
        if label in seen_labels:
            errors.append(f"Duplicate field label: '{label}'")
        seen_labels.add(label)
    
    return len(errors) == 0, errors


def load_target_fields(config_path: Optional[str] = None) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Load and validate target fields from YAML.
    
    Args:
        config_path: Path to target_fields.yaml. If None, uses default path.
        
    Returns:
        (fields_list, validation_errors)
    """
    if config_path is None:
        # Default path relative to project root
        project_root = Path(__file__).parent.parent
        config_path = project_root / "config" / "target_fields.yaml"
    else:
        config_path = Path(config_path)
    
    # Load YAML
    data = load_yaml(str(config_path))
    
    # Get fields list
    fields = data.get("fields", [])
    
    # Validate
    is_valid, errors = validate_all_fields(fields)
    
    # Return even if invalid (for inspection)
    return fields, errors


def get_field_by_id(fields: List[Dict[str, Any]], field_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a field by its id.
    
    Args:
        fields: List of field dicts
        field_id: Field id to find
        
    Returns:
        Field dict or None
    """
    for field in fields:
        if field["id"] == field_id:
            return field
    return None


def get_all_aliases(fields: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Build a mapping of all aliases to their field_id.
    
    Args:
        fields: List of field dicts
        
    Returns:
        Dict mapping alias -> field_id
    """
    alias_map = {}
    for field in fields:
        field_id = field["id"]
        for alias in field.get("aliases", []):
            alias_map[alias.lower()] = field_id
    return alias_map


def get_field_ids(fields: List[Dict[str, Any]]) -> List[str]:
    """Get list of all field ids."""
    return [f["id"] for f in fields]


def print_validation_report(fields: List[Dict[str, Any]], errors: List[str]):
    """
    Print a validation report.
    
    Args:
        fields: List of field dicts
        errors: List of validation errors
    """
    print("=" * 60)
    print("TARGET FIELDS VALIDATION REPORT")
    print("=" * 60)
    
    print(f"\n  Total fields: {len(fields)}")
    print(f"  Validation errors: {len(errors)}")
    
    if errors:
        print("\n  Errors found:")
        for error in errors:
            print(f"    - {error}")
        print("\n  Status: FAILED")
    else:
        print("\n  Status: PASSED")
    
    print("\n  First 5 field IDs:")
    for field_id in get_field_ids(fields)[:5]:
        print(f"    - {field_id}")
    
    print("=" * 60)
