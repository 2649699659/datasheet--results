"""
main.py — Datasheet Tool Entry Point

A simple 4-step datasheet extraction pipeline:
    PDF → Camelot → AI Agent → Review → Excel

Usage:
    python3 -m datasheet_tool.main --pdf path/to/datasheet.pdf --output output_dir/

Output:
    - output_dir/datasheet_extracted.json  (full extraction result)
    - output_dir/datasheet_extracted.xlsx  (Excel with 3 sheets)
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env if available
from dotenv import load_dotenv
load_dotenv()

from datasheet_tool.pdf_extractor import extract as extract_tables, RawDocument
from datasheet_tool.table_agent import extract as extract_parameters
from datasheet_tool.reviewer import review
from datasheet_tool.excel_exporter import export_from_dict
from datasheet_tool.models import ExtractionResult

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def run(pdf_path: str, output_dir: str, skip_review: bool = False, model: str = None) -> ExtractionResult:
    """
    Run the complete extraction pipeline.

    Args:
        pdf_path: Path to input PDF
        output_dir: Output directory for results
        skip_review: Skip the review step
        model: Optional LLM model override

    Returns:
        ExtractionResult
    """
    start_time = time.time()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Determine output file names
    pdf_stem = Path(pdf_path).stem
    json_path = output_path / f"{pdf_stem}_extracted.json"
    xlsx_path = output_path / f"{pdf_stem}_extracted.xlsx"

    logger.info("=" * 60)
    logger.info(f"Datasheet Tool: {pdf_path}")
    logger.info(f"Output dir: {output_dir}")
    logger.info("=" * 60)

    # Step 1: Extract raw tables with Camelot
    logger.info("Step 1: Extracting tables with Camelot...")
    doc = extract_tables(pdf_path)
    logger.info(f"  Extracted {len(doc.tables)} tables")

    # Step 2: Extract parameters with AI Agent
    logger.info("Step 2: Extracting parameters with AI Agent...")
    parameters, doc_info = extract_parameters(doc, model=model)
    logger.info(f"  Extracted {len(parameters)} parameters")

    # Step 3: Review low-confidence parameters
    if skip_review:
        logger.info("Step 3: Skipping review (--skip-review)")
    else:
        logger.info("Step 3: Reviewing low-confidence parameters...")
        parameters = review(parameters, doc, max_retries=1, model=model)
        # Update review count
        doc_info.needs_review_count = sum(1 for p in parameters if p.should_review())

    # Update processing time
    doc_info.processing_time_seconds = time.time() - start_time

    # Build result
    result = ExtractionResult(document_info=doc_info, parameters=parameters)

    # Step 4: Save results
    logger.info("Step 4: Saving results...")
    result.save_json(str(json_path))
    logger.info(f"  JSON: {json_path}")

    try:
        export_from_dict(result.to_dict(), str(xlsx_path))
        logger.info(f"  Excel: {xlsx_path}")
    except Exception as e:
        logger.warning(f"Excel export failed: {e}")

    # Summary
    elapsed = time.time() - start_time
    logger.info("=" * 60)
    logger.info(f"Complete in {elapsed:.1f}s")
    logger.info(f"Total parameters: {len(parameters)}")
    logger.info(f"Needs review: {doc_info.needs_review_count}")
    logger.info("=" * 60)

    return result


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract parameters from power module datasheets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 -m datasheet_tool.main --pdf datasheet.pdf --output output/
    python3 -m datasheet_tool.main -i datasheet.pdf -o output/ --skip-review
    python3 -m datasheet_tool.main -i datasheet.pdf -o output/ --model MiniMax-M2.7
        """
    )

    parser.add_argument("-i", "--pdf", required=True, help="Input PDF file")
    parser.add_argument("-o", "--output", required=True, help="Output directory")
    parser.add_argument("--skip-review", action="store_true", help="Skip review step")
    parser.add_argument("--model", help="LLM model override")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    setup_logging(args.verbose)

    # Check PDF exists
    if not os.path.exists(args.pdf):
        logger.error(f"PDF not found: {args.pdf}")
        sys.exit(1)

    # Check API key
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        logger.error("No API key found. Set OPENAI_API_KEY or MINIMAX_API_KEY")
        sys.exit(1)

    # Run
    try:
        run(args.pdf, args.output, skip_review=args.skip_review, model=args.model)
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
