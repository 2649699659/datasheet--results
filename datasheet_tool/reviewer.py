"""
reviewer.py — Step 3: Review and retry low-confidence parameters

Simple review logic:
- Check if parameter needs review based on simple rules
- Retry only the problematic records, not the whole table

Input:  list[Parameter], RawDocument
Output: list[Parameter] (with some retried)
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import List, Tuple

from .models import RawDocument, RawTable, Parameter

logger = logging.getLogger(__name__)

# Load prompt
REVIEW_PROMPT_PATH = Path(__file__).parent / "prompts" / "review_record.txt"


def _load_review_prompt() -> str:
    """Load the review prompt template."""
    if REVIEW_PROMPT_PATH.exists():
        return REVIEW_PROMPT_PATH.read_text(encoding="utf-8")
    return "Review and fix the following parameter extraction."


def _find_table(doc: RawDocument, page: int, table_index: int) -> RawTable | None:
    """Find a table in the document."""
    for table in doc.tables:
        if table.page == page and table.table_index == table_index:
            return table
    return None


def _format_table_for_review(table: RawTable, row_index: int, context_rows: int = 3) -> str:
    """
    Format a table for review prompt.
    Shows the target row and surrounding context.
    """
    lines = []
    
    # Show header
    if table.rows:
        lines.append("Header: | " + " | ".join(table.rows[0]) + " |")
        lines.append("")
    
    # Show target row with context
    start_idx = max(0, row_index - context_rows)
    end_idx = min(len(table.rows), row_index + context_rows + 1)
    
    for i in range(start_idx, end_idx):
        row = table.rows[i]
        marker = " --> " if i == row_index else "     "
        lines.append(f"Row {i}{marker}| " + " | ".join(row) + " |")
    
    return "\n".join(lines)


def _call_llm(prompt: str, model: str = None) -> str:
    """Call LLM API with prompt and return raw response text."""
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
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"]
            return content
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        raise RuntimeError(f"LLM API error {e.code}: {error_body}")


def _parse_review_response(content: str) -> dict:
    """Parse LLM review response."""
    content = content.strip()
    
    # Remove markdown code blocks if present
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
    
    # Find JSON boundaries
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(content[start:end])
            except json.JSONDecodeError:
                pass
        raise RuntimeError(f"Could not parse JSON from review response: {content[:200]}...")


def _retry_parameter(param: Parameter, doc: RawDocument, model: str = None) -> Parameter:
    """
    Retry extracting a single parameter.
    Returns the (possibly updated) Parameter.
    """
    logger.debug(f"Retrying parameter: {param.symbol} from page {param.page}, table {param.table_index}")
    
    # Find the source table
    table = _find_table(doc, param.page, param.table_index)
    if table is None:
        logger.warning(f"Table not found: page={param.page}, table={param.table_index}")
        return param
    
    # Format table for prompt
    table_text = _format_table_for_review(table, param.row_index)
    
    # Build parameter dict for prompt
    param_dict = {
        "symbol": param.symbol,
        "name": param.name,
        "value": param.value,
        "min": param.min,
        "typ": param.typ,
        "max": param.max,
        "unit": param.unit,
        "condition": param.condition,
        "page": param.page,
        "table_index": param.table_index,
        "row_index": param.row_index,
        "source_text": param.source_text,
        "confidence": param.confidence,
        "needs_review": param.needs_review,
    }
    
    # Build prompt
    prompt_template = _load_review_prompt()
    prompt = prompt_template.replace("{TABLE}", table_text)
    prompt = prompt.replace("{PARAMETER}", json.dumps(param_dict, indent=2))
    
    # Call LLM
    response = _call_llm(prompt, model=model)
    
    # Parse response
    reviewed = _parse_review_response(response)
    
    # Update parameter
    param.symbol = reviewed.get("symbol", param.symbol)
    param.name = reviewed.get("name", param.name)
    param.value = reviewed.get("value")
    param.min = reviewed.get("min")
    param.typ = reviewed.get("typ")
    param.max = reviewed.get("max")
    param.unit = reviewed.get("unit")
    param.condition = reviewed.get("condition")
    param.confidence = reviewed.get("confidence", param.confidence)
    param.needs_review = reviewed.get("needs_review", param.needs_review)
    param.source_text = reviewed.get("source_text", param.source_text)
    
    return param


def review(parameters: List[Parameter], doc: RawDocument, max_retries: int = 1, model: str = None) -> List[Parameter]:
    """
    Review and retry low-confidence parameters.

    Args:
        parameters: List of extracted parameters
        doc: RawDocument for table context
        max_retries: Maximum retry attempts per parameter (default 1)
        model: Optional LLM model override

    Returns:
        List of parameters (some may be updated)
    """
    # Find parameters that need review
    needs_review = [p for p in parameters if p.should_review()]
    
    if not needs_review:
        logger.info("No parameters need review")
        return parameters
    
    logger.info(f"Reviewing {len(needs_review)} parameters...")
    
    reviewed_count = 0
    for param in needs_review:
        if reviewed_count >= max_retries * 10:  # Safety limit
            logger.warning("Review limit reached, stopping")
            break
        
        issue = []
        if param.confidence < 0.8:
            issue.append(f"low confidence ({param.confidence:.2f})")
        if not param.unit and (param.value or param.min or param.typ or param.max):
            issue.append("missing unit")
        if param.unit and not (param.value or param.min or param.typ or param.max):
            issue.append("missing value")
        if not (param.value or param.min or param.typ or param.max):
            issue.append("no value at all")
        
        logger.info(f"Retrying: {param.symbol} - {', '.join(issue)}")
        
        try:
            _retry_parameter(param, doc, model=model)
            reviewed_count += 1
        except Exception as e:
            logger.warning(f"Retry failed for {param.symbol}: {e}")
    
    logger.info(f"Reviewed {reviewed_count} parameters")
    
    return parameters


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    
    if len(sys.argv) < 2:
        print("Usage: python3 reviewer.py <json_file>")
        sys.exit(1)
    
    from .models import ExtractionResult, Parameter
    
    json_path = sys.argv[1]
    result = ExtractionResult.load_json(json_path)
    
    print(f"Loaded {len(result.parameters)} parameters")
    needs_review = [p for p in result.parameters if p.should_review()]
    print(f"Need review: {len(needs_review)}")
