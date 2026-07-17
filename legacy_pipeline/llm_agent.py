"""
Optional LLM Enhancement Layer

Simple API-based LLM calls (no LangChain/LlamaIndex).

LLM is only used for:
    - Complex table parsing
    - Condition understanding
    - Parameter extraction from ambiguous text

LLM is NOT allowed to:
    - Generate values not in PDF
    - Output confirmed without source_text
    - Directly create Excel files
"""
