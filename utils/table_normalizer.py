"""
Table Normalization Utilities

Cleans tables extracted by pdfplumber.

Functions:
    - normalize_tables(tables) -> List[Table]
    - normalize_table(table) -> Table
    - remove_empty_rows(table) -> Table
    - remove_empty_columns(table) -> Table
    - clean_whitespace(cell_text) -> str

Does NOT:
    - Apply vendor-specific rules
    - Merge cells
    - Interpret cell content
"""

from typing import List, Any


def clean_whitespace(cell_text: str) -> str:
    """
    Clean whitespace in a cell.
    - Replace newlines with spaces
    - Collapse multiple spaces to one
    - Strip leading/trailing whitespace
    
    Args:
        cell_text: Raw cell text from PDF
        
    Returns:
        Cleaned cell text
    """
    if cell_text is None:
        return ""
    
    # Convert to string if not already
    text = str(cell_text)
    
    # Replace newlines and tabs with spaces
    text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    
    # Collapse multiple spaces to one
    while "  " in text:
        text = text.replace("  ", " ")
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def is_row_empty(row: List[Any], allow_zero: bool = False) -> bool:
    """
    Check if a row is empty.
    A row is empty if all cells are None, empty, or whitespace only.
    
    Args:
        row: List of cell values
        allow_zero: If True, 0 is considered non-empty
        
    Returns:
        True if row is empty
    """
    for cell in row:
        if cell is None:
            continue
        cell_str = str(cell).strip()
        if cell_str == "":
            continue
        if not allow_zero and cell_str == "0":
            continue
        # Found a non-empty cell
        return False
    return True


def is_column_empty(table: List[List[Any]], col_idx: int) -> bool:
    """
    Check if a column is empty.
    
    Args:
        table: 2D table (list of rows)
        col_idx: Column index
        
    Returns:
        True if column is empty
    """
    if not table or col_idx < 0:
        return True
    
    for row in table:
        if col_idx >= len(row):
            continue
        cell = row[col_idx]
        if cell is None:
            continue
        cell_str = str(cell).strip()
        if cell_str != "":
            return False
    return True


def remove_empty_rows(table: List[List[Any]]) -> List[List[Any]]:
    """
    Remove rows that are completely empty.
    
    Args:
        table: 2D table (list of rows)
        
    Returns:
        Table with empty rows removed
    """
    return [row for row in table if not is_row_empty(row)]


def remove_empty_columns(table: List[List[Any]]) -> List[List[Any]]:
    """
    Remove columns that are completely empty.
    
    Args:
        table: 2D table (list of rows)
        
    Returns:
        Table with empty columns removed
    """
    if not table:
        return table
    
    # Find which columns are non-empty
    num_cols = max(len(row) for row in table) if table else 0
    non_empty_cols = []
    
    for col_idx in range(num_cols):
        if not is_column_empty(table, col_idx):
            non_empty_cols.append(col_idx)
    
    # Rebuild table with only non-empty columns
    result = []
    for row in table:
        new_row = [row[i] for i in non_empty_cols if i < len(row)]
        result.append(new_row)
    
    return result


def normalize_table(table: List[List[Any]]) -> List[List[str]]:
    """
    Normalize a single table:
    - Remove empty rows
    - Remove empty columns
    - Clean cell whitespace
    
    Args:
        table: 2D table (list of rows)
        
    Returns:
        Normalized table
    """
    if not table:
        return []
    
    # Remove empty rows first
    table = remove_empty_rows(table)
    
    # Remove empty columns
    table = remove_empty_columns(table)
    
    # Clean whitespace in each cell
    result = []
    for row in table:
        cleaned_row = [clean_whitespace(cell) for cell in row]
        result.append(cleaned_row)
    
    return result


def normalize_tables(tables: List[List[List[Any]]]) -> List[List[List[str]]]:
    """
    Normalize a list of tables.
    
    Args:
        tables: List of 2D tables
        
    Returns:
        List of normalized tables
    """
    return [normalize_table(table) for table in tables]


def truncate_table(table: List[List[str]], max_rows: int = 10) -> List[List[str]]:
    """
    Truncate table to first max_rows rows for debug output.
    
    Args:
        table: 2D table
        max_rows: Maximum number of rows to keep
        
    Returns:
        Truncated table
    """
    if not table:
        return []
    return table[:max_rows]
