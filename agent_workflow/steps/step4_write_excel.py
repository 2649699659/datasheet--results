"""
step4_write_excel.py — Step 4: Write Excel Report

Generates final Excel from Agent2Result + Agent3Result.

Input:  Agent2Result, Agent3Result
Output: Excel file (.xlsx)
"""

import logging
from pathlib import Path

from ..contracts import Agent2Result, Agent3Result, FieldStatus
from ..artifacts import ArtifactPaths

logger = logging.getLogger(__name__)


def run(
    agent2_result: Agent2Result,
    agent3_result: Agent3Result,
    artifact_paths: ArtifactPaths,
) -> Path:
    """
    Write Excel report from Agent 2/3 results.

    Args:
        agent2_result: Validated params from Step 2
        agent3_result: Consistency report from Step 3
        artifact_paths: Artifact paths manager

    Returns:
        Path to generated Excel file
    """
    logger.info(f"Step 4: Writing Excel for {agent2_result.file_name}")

    excel_path = artifact_paths.step4_excel()

    # Use the reports module
    from reports.excel_from_agent import write_excel_from_agent
    write_excel_from_agent(
        agent2=agent2_result,
        agent3=agent3_result,
        output_path=str(excel_path),
    )

    logger.info(f"Step 4: Excel saved to {excel_path}")
    return excel_path


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 4:
        print("Usage: python3 step4_write_excel.py <agent2_json> <agent3_json> <output_xlsx>")
        sys.exit(1)

    from artifacts import load_agent2, load_agent3
    from pathlib import Path

    agent2_path = Path(sys.argv[1])
    agent3_path = Path(sys.argv[2])
    output_path = Path(sys.argv[3])

    agent2 = load_agent2(agent2_path)
    agent3 = load_agent3(agent3_path)

    from reports.excel_from_agent import write_excel_from_agent
    write_excel_from_agent(agent2, agent3, str(output_path))
    print(f"\nExcel saved to: {output_path}")
