#!/usr/bin/env python3
"""
Evaluation script for AI extraction results.
This is separate from extraction - it contains known answers for evaluation only.
"""

import os
import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# Evaluation cases - these are for TESTING ONLY, not in extraction prompt
EVALUATION_CASES = {
    "wolfspeed_cab530_pages_1_3": {
        "description": "Wolfspeed CAB530M12BM3, Pages 1-3",
        "targets": [
            {"symbol": "Ciss", "value": "39.6", "unit": "nF", "check": "value_match"},
            {"symbol": "Coss", "value": "1.4", "unit": "nF", "check": "value_match"},
            {"symbol": "Crss", "value": "84", "unit": "pF", "check": "value_match"},
            {"symbol": "QG", "value": "1362", "unit": "nC", "check": "value_match"},
            {"symbol": "Rth JC", "value": "0.065", "unit": "°C/W", "check": "value_match"},
            {"symbol": "Err", "value": None, "unit": "mJ", "check": "exists"},
            {"symbol": "Weight", "value": "300", "unit": "g", "check": "value_match"},
            {"symbol": "Visol", "value": "5", "unit": "kV", "check": "value_match"},
            {"symbol": "Clearance", "value": None, "unit": "mm", "check": "exists"},
            {"symbol": "Creepage", "value": None, "unit": "mm", "check": "exists"},
        ],
    },
}


def load_json(json_path: str) -> dict:
    """Load JSON, trying normalized version if original not found."""
    if not os.path.exists(json_path):
        # Try normalized version
        normalized_path = json_path.replace(".json", "_normalized.json")
        if os.path.exists(normalized_path):
            print(f"Using normalized JSON: {normalized_path}")
            json_path = normalized_path
        else:
            raise FileNotFoundError(f"JSON file not found: {json_path}")
    
    with open(json_path) as f:
        return json.load(f)


def evaluate(json_path: str, case: str) -> dict:
    """Evaluate extraction results against known targets."""
    
    data = load_json(json_path)
    
    params = data.get("parameters", [])
    case_data = EVALUATION_CASES.get(case)
    
    if not case_data:
        raise ValueError(f"Unknown evaluation case: {case}. Available: {list(EVALUATION_CASES.keys())}")
    
    print(f"\n{'='*60}")
    print(f" EVALUATION: {case_data['description']}")
    print(f"{'='*60}")
    print(f"JSON: {json_path}")
    print(f"Total extracted parameters: {len(params)}")
    
    # Status breakdown
    confirmed = [p for p in params if p.get("status") == "confirmed"]
    needs_review = [p for p in params if p.get("status") == "needs_review"]
    needs_alias = [p for p in params if p.get("status") == "needs_alias_review"]
    
    print(f"\nStatus breakdown:")
    print(f"  confirmed: {len(confirmed)}")
    print(f"  needs_review: {len(needs_review)}")
    print(f"  needs_alias_review: {len(needs_alias)}")
    
    # Source text check
    with_source = []
    without_source = []
    for p in params:
        st = (p.get("source_text") or "").strip()
        if st and st not in ["-", "—", "N/A"]:
            with_source.append(p)
        else:
            without_source.append(p)
    
    print(f"\nsource_text check:")
    print(f"  with valid source_text: {len(with_source)}")
    print(f"  without / placeholder: {len(without_source)}")
    
    # Normalizer stats if available
    if "normalizer_stats" in data:
        ns = data["normalizer_stats"]
        print(f"\nNormalizer stats:")
        print(f"  unit fixed: {ns.get('unit_fixed', 0)}")
        print(f"  symbol alias fixed: {ns.get('symbol_alias_fixed', 0)}")
        print(f"  symbol inferred: {ns.get('symbol_inferred', 0)}")
        print(f"  condition fixed: {ns.get('condition_fixed', 0)}")
    
    # Target evaluation
    targets = case_data["targets"]
    hits = 0
    misses = 0
    details = []
    
    print(f"\nTarget evaluation ({len(targets)} targets):")
    print("-"*60)
    
    for target in targets:
        sym = target["symbol"]
        check_type = target["check"]
        expected_val = target.get("value")
        expected_unit = target.get("unit")
        
        # Find matching parameters - be flexible about symbol matching
        matched = []
        for p in params:
            p_sym = (p.get("symbol") or "").strip()
            
            # Exact match or substring match
            if (p_sym == sym or 
                sym.lower() in p_sym.lower() or 
                p_sym.lower() in sym.lower() or
                _symbols_match(p_sym, sym)):
                
                val = p.get("typ") or p.get("value") or p.get("min") or p.get("max")
                unit = (p.get("unit") or "").strip()
                status = p.get("status", "?")
                
                if check_type == "exists":
                    if val is not None and str(val).strip() not in ["", "-", "—", "None"]:
                        matched.append({"param": p, "val": val, "unit": unit, "status": status})
                elif check_type == "value_match":
                    if val is not None and str(val).strip():
                        val_str = str(val).strip()
                        expected_str = str(expected_val).strip() if expected_val else ""
                        # Compare numeric values (handle float precision)
                        try:
                            val_num = float(val_str)
                            exp_num = float(expected_str)
                            if abs(val_num - exp_num) < 0.001:
                                if expected_unit is None or _units_match(unit, expected_unit):
                                    matched.append({"param": p, "val": val, "unit": unit, "status": status})
                        except (ValueError, TypeError):
                            # String comparison
                            if val_str == expected_str:
                                if expected_unit is None or _units_match(unit, expected_unit):
                                    matched.append({"param": p, "val": val, "unit": unit, "status": status})
        
        if matched:
            hit = True
            print(f"  ✅ {sym}: FOUND", end="")
            for m in matched[:2]:
                status_marker = " [confirmed]" if m["status"] == "confirmed" else f" [{m['status']}]"
                print(f" ({m['val']} {m['unit']}{status_marker})", end="")
            print()
            hits += 1
        else:
            print(f"  ❌ {sym}: NOT FOUND", end="")
            if expected_val:
                print(f" (expected {expected_val} {expected_unit or ''})", end="")
            print()
            misses += 1
        
        details.append({"symbol": sym, "found": bool(matched), "expected": expected_val, "matched": matched})
    
    print()
    hit_rate = hits / len(targets) * 100 if targets else 0
    print(f"Target hit rate: {hits}/{len(targets)} = {hit_rate:.1f}%")
    
    # Unknown parameters sample
    print()
    print("Sample unclassified / needs_alias_review parameters:")
    unclassified_count = 0
    for p in params:
        sym = (p.get("symbol") or "").strip()
        val = p.get("typ") or p.get("value") or p.get("min") or "-"
        if len(sym) > 2:  # Skip short common symbols
            known_symbols = {"Ciss", "Coss", "Crss", "Eon", "Eoff", "Err", "QRR", "trr",
                             "RDS(on)", "Rth JC", "Rth JH", "VDS", "VGS", "VGS(th)", "V(BR)DSS",
                             "ID", "IDSS", "IGSS", "IDM", "IF", "IR", "gfs", "RG(int)",
                             "QG", "QGS", "QGD", "VF", "Visol", "Clearance", "Creepage",
                             "Weight", "Lstray", "TC", "TJ", "TVJ", "PD", "EON", "EOFF"}
            if sym not in known_symbols:
                unclassified_count += 1
                if unclassified_count <= 10:
                    unit = p.get("unit", "")
                    status = p.get("status", "?")
                    print(f"  ? {sym}: {val} {unit} [{status}]")
    
    print(f"  ... (total unclassified: {unclassified_count})")
    
    return {
        "case": case,
        "total_params": len(params),
        "confirmed": len(confirmed),
        "needs_review": len(needs_review),
        "needs_alias_review": len(needs_alias),
        "with_source_text": len(with_source),
        "target_hits": hits,
        "target_misses": misses,
        "target_hit_rate": hit_rate,
    }


def _symbols_match(a: str, b: str) -> bool:
    """Check if two symbols match (flexible)."""
    a = a.lower().replace("_", "").replace("-", "").replace(" ", "")
    b = b.lower().replace("_", "").replace("-", "").replace(" ", "")
    return a == b or a in b or b in a


def _units_match(a: str, b: str) -> bool:
    """Check if two units match."""
    a = a.lower().replace("μ", "u").replace(" ", "").replace("·", "")
    b = b.lower().replace("μ", "u").replace(" ", "").replace("·", "")
    return a == b or a in b or b in a


def main():
    parser = argparse.ArgumentParser(description="Evaluate AI extraction results")
    parser.add_argument("--json", type=str, required=True, help="Path to extraction JSON")
    parser.add_argument("--case", type=str, required=True, 
                        help=f"Evaluation case. Available: {list(EVALUATION_CASES.keys())}")
    args = parser.parse_args()
    
    result = evaluate(args.json, args.case)
    
    print()
    print("="*60)
    print(" FINAL REPORT")
    print("="*60)
    print(f"  Total parameters: {result['total_params']}")
    print(f"  confirmed: {result['confirmed']}")
    print(f"  needs_review: {result['needs_review']}")
    print(f"  needs_alias_review: {result['needs_alias_review']}")
    print(f"  with source_text: {result['with_source_text']}")
    print(f"  Target hit rate: {result['target_hit_rate']:.1f}% ({result['target_hits']}/{result['target_misses']+result['target_hits']})")
    print("="*60)
    
    return result


if __name__ == "__main__":
    main()
