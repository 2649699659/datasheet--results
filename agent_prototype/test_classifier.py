#!/usr/bin/env python3
"""
Agent 1 Prototype Test Script

Usage:
    # Step 1: Generate prompts for LLM
    python3 test_classifier.py --mode generate_prompts
    
    # Step 2: Run with LLM and save results to results/llm_responses.json
    
    # Step 3: Compare LLM results with current pipeline
    python3 test_classifier.py --mode compare

    # Or run all steps (if LLM available)
    python3 test_classifier.py --mode all
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def generate_prompts(test_rows, output_dir):
    """Generate individual prompt files for each test row."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    prompts = []
    for i, row in enumerate(test_rows):
        # Build the input JSON manually to avoid format issues
        input_json = json.dumps({
            'page_number': row['page_number'],
            'table_index': row['table_index'],
            'row_index': row['row_index'],
            'row_cells': row['row_cells'],
            'row_text': row.get('row_text', '')[:200],
        }, ensure_ascii=False, indent=2)
        
        # Escape curly braces for template replacement
        input_json_escaped = input_json.replace('{', '{{').replace('}', '}}')
        
        prompt = f"""# Agent 1: Table Row Classifier

## 任务

你是一个 SiC MOSFET 模块 datasheet 参数分类器。

给定一行 Camelot 提取的 datasheet 表格数据，判断这是什么参数。

## 目标参数列表

只识别以下 5 个参数：

| field_id | 英文名 | 典型符号 |
|----------|--------|----------|
| voltage_rating | Drain-Source Voltage | VDS |
| current_rating | Drain Current | ID |
| rds_on_25c | RDS(on) @25°C | RDS(on) |
| vgs_th | Gate Threshold Voltage | VGS(th) |
| trr | Reverse Recovery Time | tRR, trr |

## 输入数据

```json
{input_json_escaped}
```

## 输出格式

输出严格 JSON，不要 markdown：

```json
{{
  "is_target_parameter": true/false,
  "field_id": "voltage_rating" / null,
  "confidence": 0.0-1.0,
  "extracted_values": {{"min": null, "typ": null, "max": null, "value": null}},
  "unit": "V" / null,
  "condition": "TC=25°C" / null,
  "reasoning": "为什么判断",
  "warnings": []
}}
```

## 判断标准

### voltage_rating (VDS)
- 符号列包含 "VDS" 或 "Drain-Source Voltage"
- 单位是 V
- 值通常是 1200, 1700 等

### current_rating (ID)
- 符号列包含 "ID" 或 "Drain Current"
- 单位是 A
- 通常有 "continuous" 或 "pulsed"

### rds_on_25c
- 符号列包含 "RDS(on)"
- 单位是 mΩ
- 条件必须包含 TC=25°C

### vgs_th
- 符号列包含 "VGS(th)" 或 "Gate Threshold Voltage"
- 单位是 V
- 值通常是范围如 2-4 V

### trr
- 符号列包含 "tRR" 或 "trr"
- 单位是 ns

## 输出要求

只输出 JSON，不要其他文字。"""
        
        prompts.append({
            'test_index': i,
            'field_id': row['target_field'],
            'page': row['page_number'],
            'table': row['table_index'],
            'row': row['row_index'],
            'row_text': row.get('row_text', '')[:100],
            'prompt': prompt,
        })
        
        # Save individual prompt file
        filename = f"prompt_{i:03d}_{row['target_field']}.txt"
        with open(output_dir / filename, 'w') as f:
            f.write(prompt)
    
    # Save index
    with open(output_dir / 'prompt_index.json', 'w') as f:
        json.dump(prompts, f, ensure_ascii=False, indent=2)
    
    print(f"Generated {len(prompts)} prompts in {output_dir}/")
    return prompts


def load_current_pipeline_results():
    """Load current pipeline results for comparison."""
    sel_path = Path('output/selected_params_debug.json')
    if not sel_path.exists():
        print("Warning: selected_params_debug.json not found")
        return None
    
    with open(sel_path, 'r') as f:
        data = json.load(f)
    
    # Extract relevant fields
    results = {}
    for doc in data.get('documents', []):
        for field in doc.get('fields', []):
            fid = field.get('field_id')
            if fid in ['voltage_rating', 'current_rating', 'rds_on_25c', 'vgs_th', 'trr']:
                sel = field.get('selected_param', {})
                results[fid] = {
                    'status': field.get('selection_status'),
                    'value': sel.get('value') or sel.get('typ') or f"{sel.get('min')}-{sel.get('max')}",
                    'unit': sel.get('unit'),
                    'condition': sel.get('condition'),
                    'source_text': sel.get('source_text', '')[:100],
                    'source_page': sel.get('source_page'),
                    'source_table': sel.get('table_index'),
                    'source_row': sel.get('row_index'),
                }
    
    return results


def compare_results(llm_results, pipeline_results, test_rows):
    """Compare LLM results with current pipeline results."""
    comparison = {
        'timestamp': datetime.now().isoformat(),
        'total_test_rows': len(test_rows),
        'llm_results_count': len(llm_results) if llm_results else 0,
        'pipeline_results_count': len(pipeline_results) if pipeline_results else 0,
        'by_field': {},
        'discrepancies': [],
    }
    
    if not pipeline_results:
        print("No pipeline results to compare with")
        return comparison
    
    # Group test rows by target field
    by_field = {}
    for row in test_rows:
        fid = row['target_field']
        if fid not in by_field:
            by_field[fid] = []
        by_field[fid].append(row)
    
    # Compare each field
    for fid in sorted(by_field.keys()):
        rows = by_field[fid]
        pipe = pipeline_results.get(fid, {})
        
        comparison['by_field'][fid] = {
            'test_rows_count': len(rows),
            'pipeline_status': pipe.get('status'),
            'pipeline_value': pipe.get('value'),
            'pipeline_unit': pipe.get('unit'),
            'pipeline_source_page': pipe.get('source_page'),
        }
        
        # Check if LLM found the same field
        if llm_results:
            llm_found = [r for r in llm_results if r.get('field_id') == fid and r.get('is_target_parameter')]
            comparison['by_field'][fid]['llm_found_count'] = len(llm_found)
            
            if llm_found and pipe:
                # Compare values
                first_llm = llm_found[0]
                llm_val = first_llm.get('extracted_values', {})
                pipe_val = pipe.get('value')
                
                # Check if values match
                if llm_val and pipe_val:
                    match = False
                    if llm_val.get('value') == pipe_val:
                        match = True
                    elif abs(llm_val.get('typ') or 0 - float(str(pipe_val).split()[0] if pipe_val else 0)) < 0.1:
                        match = True
                    
                    comparison['by_field'][fid]['value_match'] = match
                    
                    if not match:
                        comparison['discrepancies'].append({
                            'field_id': fid,
                            'llm_value': llm_val,
                            'pipeline_value': pipe_val,
                        })
    
    return comparison


def main():
    parser = argparse.ArgumentParser(description='Agent 1 Prototype Test')
    parser.add_argument(
        '--mode',
        choices=['generate_prompts', 'compare', 'all'],
        default='generate_prompts',
        help='Test mode'
    )
    parser.add_argument(
        '--test-data',
        default='agent_prototype/data/test_rows.json',
        help='Path to test data'
    )
    parser.add_argument(
        '--llm-results',
        default='agent_prototype/results/llm_responses.json',
        help='Path to LLM results for comparison'
    )
    parser.add_argument(
        '--prompts-dir',
        default='agent_prototype/results/prompts',
        help='Directory for generated prompts'
    )
    
    args = parser.parse_args()
    
    # Load test data
    print(f"Loading test data from {args.test_data}...")
    with open(args.test_data, 'r') as f:
        test_data = json.load(f)
    
    test_rows = test_data['test_rows']
    print(f"Loaded {len(test_rows)} test rows")
    print(f"Test parameters: {test_data['test_parameters']}")
    
    if args.mode in ['generate_prompts', 'all']:
        print(f"\nGenerating prompts...")
        prompts = generate_prompts(test_rows, args.prompts_dir)
        
        # Also create a combined prompt file for batch processing
        combined_prompt = "# Agent 1 Prototype - Batch Test\n\n"
        combined_prompt += f"Total test rows: {len(test_rows)}\n\n"
        
        for p in prompts[:10]:  # First 10 as preview
            combined_prompt += f"\n## Test {p['test_index']}: {p['field_id']}\n"
            combined_prompt += f"Page {p['page']}, Table {p['table']}, Row {p['row']}\n"
            combined_prompt += f"Row text: {p['row_text']}\n\n"
            combined_prompt += "---\n\n"
        
        combined_prompt += f"\n... and {len(prompts) - 10} more rows\n"
        
        with open('agent_prototype/results/batch_prompt_preview.txt', 'w') as f:
            f.write(combined_prompt)
        
        print(f"\nPrompt preview saved to agent_prototype/results/batch_prompt_preview.txt")
    
    if args.mode in ['compare', 'all']:
        print("\nLoading current pipeline results...")
        pipeline_results = load_current_pipeline_results()
        
        if pipeline_results:
            print(f"Loaded {len(pipeline_results)} pipeline results")
            for fid, res in sorted(pipeline_results.items()):
                print(f"  {fid}: {res.get('status')} - {res.get('value')} {res.get('unit')}")
        
        # Load LLM results if available
        llm_results = None
        llm_path = Path(args.llm_results)
        if llm_path.exists():
            print(f"\nLoading LLM results from {args.llm_results}...")
            with open(llm_path, 'r') as f:
                llm_results = json.load(f)
            print(f"Loaded {len(llm_results) if isinstance(llm_results, list) else 'invalid'} LLM results")
        
        # Compare
        print("\nComparing results...")
        comparison = compare_results(llm_results, pipeline_results, test_rows)
        
        # Save comparison
        with open('agent_prototype/results/comparison.json', 'w') as f:
            json.dump(comparison, f, ensure_ascii=False, indent=2)
        
        print(f"\nComparison saved to agent_prototype/results/comparison.json")
        
        # Print summary
        print("\n" + "=" * 60)
        print("COMPARISON SUMMARY")
        print("=" * 60)
        
        for fid, data in comparison.get('by_field', {}).items():
            print(f"\n{fid}:")
            print(f"  Test rows: {data['test_rows_count']}")
            print(f"  LLM found: {data.get('llm_found_count', 'N/A')}")
            print(f"  Pipeline: {data['pipeline_status']} - {data['pipeline_value']} {data['pipeline_unit']}")
            if 'value_match' in data:
                print(f"  Value match: {data['value_match']}")
        
        if comparison.get('discrepancies'):
            print(f"\n⚠️  {len(comparison['discrepancies'])} discrepancies found")
    
    print("\n" + "=" * 60)
    print("Next steps:")
    print("1. Run prompts with LLM (Claude/GPT-4)")
    print("2. Save results to agent_prototype/results/llm_responses.json")
    print("3. Run: python3 test_classifier.py --mode compare")
    print("=" * 60)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
