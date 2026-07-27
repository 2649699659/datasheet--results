"""
table_agent.py — Step 2: AI Agent extracts parameters from tables

Uses a single LLM call to extract all parameters from the raw tables.
No multi-agent, no enrichment, no complex status.

Input:  RawDocument (from pdf_extractor)
Output: list[Parameter], DocumentInfo
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import List, Tuple

from .models import RawDocument, RawTable, Parameter, DocumentInfo

logger = logging.getLogger(__name__)

# Load prompt
PROMPT_PATH = Path(__file__).parent / "prompts" / "extract_table.txt"


def _load_prompt() -> str:
    """Load the extraction prompt template."""
    if PROMPT_PATH.exists():
        return PROMPT_PATH.read_text(encoding="utf-8")
    # Fallback prompt
    return """Extract parameters from the following datasheet tables. Return JSON with metadata and parameters."""


def _format_tables_for_prompt(doc: RawDocument, max_rows_per_table: int = 30) -> str:
    """Format raw tables for LLM prompt."""
    table_texts = []
    
    for table in doc.tables:
        page_num = table.page
        table_idx = table.table_index
        
        if not table.rows:
            continue
        
        lines = []
        lines.append(f"\n### Page {page_num}, Table {table_idx}\n")
        
        # Header row
        header_cells = table.rows[0]
        lines.append("| " + " | ".join(header_cells) + " |")
        lines.append("|" + "|".join(["---"] * len(header_cells)) + "|")
        
        # Data rows (limited)
        for i, row in enumerate(table.rows[1:max_rows_per_table + 1], start=1):
            lines.append("| " + " | ".join(row) + " |")
        
        if len(table.rows) > max_rows_per_table + 1:
            lines.append(f"... ({len(table.rows) - max_rows_per_table - 1} more rows)")
        
        table_texts.append("\n".join(lines))
    
    return "\n\n".join(table_texts)


def _call_llm(prompt: str, model: str = None) -> str:
    """Call LLM API with prompt and return raw response text."""
    # Check environment for API credentials
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        raise RuntimeError("No API key found (OPENAI_API_KEY or MINIMAX_API_KEY)")
    
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.minimaxi.chat/v1")
    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    
    if model is None:
        model = os.environ.get("LLM_MODEL", "MiniMax-M2.7")
    
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "top_p": 1,
        "seed": 42,
    }
    
    import urllib.request
    import urllib.error
    
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=300) as response:
            result = json.loads(response.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"]
            return content
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        raise RuntimeError(f"LLM API error {e.code}: {error_body}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse LLM response: {e}")


def _parse_json_response(content: str) -> Tuple[dict, List[dict]]:
    """
    Parse LLM JSON response.
    Returns (metadata_dict, parameters_list).
    """
    # Try to find JSON in the response
    content = content.strip()
    
    # Remove markdown code blocks if present
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
    
    # Find JSON boundaries
    try:
        data = json.loads(content)
        return data.get("metadata", {}), data.get("parameters", [])
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                data = json.loads(content[start:end])
                return data.get("metadata", {}), data.get("parameters", [])
            except json.JSONDecodeError:
                pass
        raise RuntimeError(f"Could not parse JSON from LLM response: {content[:200]}...")


def extract(doc: RawDocument, model: str = None) -> Tuple[List[Parameter], DocumentInfo]:
    """
    Extract parameters from raw document using LLM.

    Args:
        doc: RawDocument from pdf_extractor
        model: Optional LLM model override

    Returns:
        Tuple of (list of Parameter, DocumentInfo)
    """
    logger.info(f"Extracting parameters from {len(doc.tables)} tables...")
    start_time = time.time()
    
    # Build prompt
    prompt_template = _load_prompt()
    tables_text = _format_tables_for_prompt(doc)
    prompt = prompt_template.replace("{TABLES}", tables_text)
    
    # Call LLM
    logger.info("Calling LLM...")
    response = _call_llm(prompt, model=model)
    
    # Parse response
    logger.info("Parsing LLM response...")
    metadata_dict, params_list = _parse_json_response(response)
    
    # Convert to Parameter objects
    parameters = []
    for p in params_list:
        param = Parameter(
            symbol=p.get("symbol"),
            name=p.get("name"),
            value=p.get("value"),
            min=p.get("min"),
            typ=p.get("typ"),
            max=p.get("max"),
            unit=p.get("unit"),
            condition=p.get("condition"),
            page=p.get("page", 0),
            table_index=p.get("table_index", 0),
            row_index=p.get("row_index", 0),
            source_text=p.get("source_text"),
            confidence=p.get("confidence", 1.0),
            needs_review=p.get("needs_review", False),
        )
        parameters.append(param)
    
    # Build DocumentInfo
    doc_info = DocumentInfo(
        manufacturer=metadata_dict.get("manufacturer"),
        part_number=metadata_dict.get("part_number"),
        module_type=metadata_dict.get("module_type"),
        description=metadata_dict.get("description"),
        file_name=doc.file_name,
        pdf_path=doc.pdf_path,
        processing_time_seconds=time.time() - start_time,
        total_parameters=len(parameters),
        needs_review_count=sum(1 for p in parameters if p.needs_review or p.should_review()),
    )
    
    logger.info(f"Extracted {len(parameters)} parameters in {doc_info.processing_time_seconds:.1f}s")
    
    return parameters, doc_info


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
    if len(sys.argv) < 2:
        print("Usage: python3 table_agent.py <pdf_path>")
        sys.exit(1)
    
    from .pdf_extractor import extract as extract_tables
    
    pdf_path = sys.argv[1]
    doc = extract_tables(pdf_path)
    parameters, doc_info = extract(doc)
    
    print(f"\nExtracted {len(parameters)} parameters:")
    print(f"  Manufacturer: {doc_info.manufacturer}")
    print(f"  Part Number: {doc_info.part_number}")
    print(f"  Module Type: {doc_info.module_type}")
    
    for p in parameters[:10]:
        print(f"  {p.symbol}: {p.typ or p.value} {p.unit}")
