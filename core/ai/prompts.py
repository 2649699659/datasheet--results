"""
AI Prompts for generic table extraction.
"""
from typing import Optional


def build_page_extraction_prompt(
    part_number: str,
    manufacturer: str,
    page_number: int,
    page_text: str,
    raw_tables: str,
    text_blocks: str = "",
) -> str:
    """
    Build prompt for extracting parameters from a single page.
    
    This prompt is MANUFACTURER-AGNOSTIC. It contains no specific target
    values, manufacturer names, or example data from any particular datasheet.
    """
    prompt = f"""# Power Semiconductor Datasheet - Generic Parameter Extraction

You are extracting structured parameters from a power semiconductor datasheet page.
Extract every explicitly listed parameter row from the provided page text and table text.

## Document Info
- Part Number: {part_number}
- Manufacturer: {manufacturer}
- Page: {page_number}

## Data Source (Markdown Tables)
```
{raw_tables}
```

## Critical Table Structure Rules

The data above is formatted as markdown tables. The column headers are shown
above each "Rows:" section. Common columns include:

- Parameter (the parameter name)
- Symbol (the variable symbol, e.g., Ciss, Coss, QG)
- Min / Typ / Max (numerical values)
- Unit (the measurement unit, e.g., nF, mΩ, V, nC)
- Conditions (test conditions)

**IMPORTANT RULES FOR TABLE EXTRACTION:**

1. **USE THE UNIT COLUMN**: If a row has a value but the symbol row does not include a unit, look at the "Unit" column for that row and include it in the "unit" field.

2. **USE THE CONDITIONS COLUMN**: If a row has a value but no explicit condition, look at the "Conditions" column and include those conditions.

3. **PRESERVE SECTION HEADINGS**: If a table has a section heading (e.g., "Clearance Distance", "Creepage Distance", "Weight", "Isolation Voltage"), apply that heading to all rows in that section.

4. **INHERITED HEADINGS**: Some mechanical tables list the parameter type as a sub-heading (e.g., "Terminal to Terminal" under "Clearance Distance"). Inherit the main heading and use the sub-heading as the condition.

5. **RAW ROW**: For each extracted row, include the raw text from the table row as "raw_row". This is essential for verification.

6. **TABLE CONTEXT**: For each row, include a brief "table_context" describing the table section it came from (e.g., {{"table_title": "MOSFET Characteristics", "inherited_heading": "Gate Charge"}}).

7. **DO NOT OUTPUT "None" AS UNIT**: If the table has a Unit column but the cell is blank or empty, do NOT put "None" in the unit field. Leave it null.

8. **DO NOT INVENT VALUES**: If the Unit column is blank, do not guess the unit. Leave it null.

## Output Schema

For each parameter row found, return ALL of the following fields:
- category: one of "ratings", "static", "dynamic", "switching", "thermal", "mechanical", "insulation", or "general"
- section: the table or section name (e.g., "MOSFET Characteristics", "Mechanical Specifications")
- symbol: the parameter symbol as shown in the table (e.g., "Ciss", "RDS(on)", "QG")
- parameter: the full parameter name (e.g., "Input Capacitance", "Total Gate Charge")
- min: minimum value if present and numeric, otherwise null
- typ: typical value if present and numeric, otherwise null
- max: maximum value if present and numeric, otherwise null
- value: single value if no min/typ/max distinction, otherwise null
- unit: the EXACT unit string from the Unit column (e.g., "nF", "mΩ", "V", "nC"), NOT "None" or empty string
- condition: the EXACT test condition from the Conditions column
- source_page: {page_number}
- source_text: the EXACT text string copied from the table row (the raw row text, enough to uniquely identify it)
- raw_row: the full original table row text as it appears in the table
- table_context: {{"table_title": "...", "inherited_heading": "..."}} or null if not applicable
- status: "confirmed" if extracted from valid source with complete data, "needs_review" otherwise
- confidence: 0.5-1.0 based on extraction clarity

## Mechanical / Insulation Parameters

For parameters without explicit symbols in the table:

9. **Clearance Distance**: Look for "Clearance" or "Clearance Distance" as section headers. Use symbol="Clearance", parameter="Clearance Distance". Use the sub-row (e.g., "Terminal to Terminal") as condition.

10. **Creepage Distance**: Look for "Creepage" or "Creepage Distance" as section headers. Use symbol="Creepage", parameter="Creepage Distance". Use the sub-row as condition.

11. **Weight**: Look for "Weight" or "Weight (g)" as parameter or section. Use symbol="Weight", parameter="Weight". Include unit "g".

12. **Isolation Voltage**: Look for "Isolation Voltage", "Visol", or "Dielectric Strength" sections. Use symbol="Visol", parameter="Isolation Voltage". Include unit "kV".

13. **Mounting Torque**: Use symbol="Mounting Torque", parameter="Mounting Torque". Include unit "N-m".

14. **Stray Inductance**: Look for "Stray Inductance" or "Lstray" sections. Use symbol="Lstray", parameter="Stray Inductance". Include unit "nH".

## General Rules

15. Extract ONLY values explicitly present in the provided text.
16. Do not infer, calculate, or estimate values.
17. Do not use prior knowledge about the manufacturer or typical values.
18. Do not use values from other pages unless included in the current input.
19. Preserve all three of min/typ/max when present.
20. Do not collapse a range into a single value.
21. If a value is absent, leave the field null.
22. Do not output "None" for unit or condition if the table cell is blank.
23. Placeholder values ("-", "—", "N/A") must NOT be marked confirmed.
24. Every row must have source_text and raw_row filled in.
25. If TEXT FALLBACK BLOCKS are provided, use them to recover section context for mechanical/isolation parameters.
26. When a table row has no symbol, look at TEXT FALLBACK BLOCKS for the section heading and use it as parameter/section context.
27. When extracting from TEXT FALLBACK BLOCKS, include the full heading text in source_text.

## TEXT FALLBACK BLOCKS

Use the following text blocks to recover section context when table rows lack headings:

- **Clearance Distance**: If a value appears under "Clearance Distance", use symbol="Clearance", parameter="Clearance Distance", category="mechanical".
- **Creepage Distance**: If a value appears under "Creepage Distance", use symbol="Creepage", parameter="Creepage Distance", category="mechanical".
- **Isolation Voltage**: If a value appears under "Isolation Voltage" or "Visol", use symbol="Visol", parameter="Isolation Voltage", category="insulation".
- **Weight**: If a value appears under "Weight", use symbol="Weight", parameter="Weight", category="mechanical".
- **Mounting Torque**: If a value appears under "Mounting Torque", use symbol="Mounting Torque", parameter="Mounting Torque", category="mechanical".
- **Stray Inductance**: If a value appears under "Stray Inductance" or "Lstray", use symbol="Lstray", parameter="Stray Inductance", category="mechanical".
- When using TEXT FALLBACK BLOCKS, the source_text should include both the value and the inherited heading text.
- Only extract values that are explicitly present in the TEXT FALLBACK BLOCKS; do not infer.

## Output Format

Return a single valid JSON object with no markdown:
{{
  "page": {page_number},
  "parameters": [
    {{
      "category": "dynamic",
      "section": "MOSFET Characteristics",
      "symbol": "Ciss",
      "parameter": "Input Capacitance",
      "min": null,
      "typ": "39.6",
      "max": null,
      "value": null,
      "unit": "nF",
      "condition": "VGS=0V; VDS=800V; f=100kHz",
      "source_page": {page_number},
      "source_text": "Ciss | Input Capacitance | | 39.6 | | nF | VGS=0V; VDS=800V",
      "raw_row": "Ciss | Input Capacitance | | 39.6 | | nF | VGS=0V; VDS=800V; f=100kHz",
      "table_context": {{"table_title": "MOSFET Characteristics", "inherited_heading": null}},
      "status": "confirmed",
      "confidence": 0.95
    }}
  ]
}}

Pure JSON only. If no parameters found: {{"page": {page_number}, "parameters": []}}
"""
    return prompt


def build_summary_prompt(
    part_number: str,
    manufacturer: str,
    page_results: list,
) -> str:
    """
    Build prompt for post-processing and consolidating page-level results.
    """
    import json
    pages_json = json.dumps(page_results, indent=2)
    
    prompt = f"""# Post-Process Extracted Parameters

You are reviewing and consolidating parameters extracted from multiple pages of a power semiconductor datasheet.

## Document Info
- Part Number: {part_number}
- Manufacturer: {manufacturer}

## Extracted Parameters from All Pages
```json
{pages_json}
```

## Tasks

1. **Deduplicate**: If the same parameter appears on multiple pages with the same value and condition, keep only one
2. **Resolve conflicts**: If the same parameter appears with different values on different pages, keep both as separate entries with different conditions
3. **Validate source_text**: Ensure every entry has a valid source_text and raw_row
4. **Assign section names**: Add appropriate section names based on table_context
5. **Set status**: Mark entries with empty values or missing source_text as "needs_review"

## Output Format

Return a single valid JSON object:
```json
{{
  "part_number": "{part_number}",
  "manufacturer": "{manufacturer}",
  "parameters": [...]
}}
```

Pure JSON only. No markdown or explanation.
"""
    return prompt
