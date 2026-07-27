"""
datasheet_tool — Simplified datasheet extraction

A minimal 4-step pipeline:
    PDF → Camelot → AI Agent → Review → Excel

Modules:
- pdf_extractor: Camelot table extraction
- table_agent: LLM-based parameter extraction
- reviewer: Low-confidence parameter review
- excel_exporter: Excel output
- models: Data structures
"""

__version__ = "1.0.0"
