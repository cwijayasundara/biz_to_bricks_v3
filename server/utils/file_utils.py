"""
File utility functions for the Document Processing API.
"""

from pathlib import Path as FilePath
from typing import Optional
from config import (
    UPLOADED_FILE_PATH, 
    PARSED_FILE_PATH, 
    GENERATED_QUESTIONS_PATH,
    EXCEL_EXTENSIONS,
    CSV_EXTENSIONS
)
from file_util_enhanced import create_directory


def get_file_path(directory: str, filename: str, extension: Optional[str] = None) -> str:
    """
    Construct file path with proper handling.
    
    Args:
        directory: The target directory
        filename: The filename 
        extension: Optional extension to append
        
    Returns:
        Constructed file path as string
    """
    if extension:
        # Use pathlib to properly extract base filename without extension
        base_name = FilePath(filename).stem
        return str(FilePath(directory) / f"{base_name}{extension}")
    return str(FilePath(directory) / filename)


def is_excel_or_csv_file(filename: str) -> bool:
    """
    Check if a file is an Excel or CSV file based on its extension.
    
    Args:
        filename: The filename to check
        
    Returns:
        True if file is Excel or CSV, False otherwise
    """
    if not filename:
        return False
    
    extension = FilePath(filename).suffix.lower()
    return extension in (EXCEL_EXTENSIONS + CSV_EXTENSIONS)


def get_file_type(filename: str) -> str:
    """
    Get the file type (csv, excel, or unknown) based on extension.
    
    Args:
        filename: The filename to analyze
        
    Returns:
        File type as string: 'csv', 'excel', or 'unknown'
    """
    if not filename:
        return "unknown"
    
    extension = FilePath(filename).suffix.lower()
    if extension in CSV_EXTENSIONS:
        return "csv"
    elif extension in EXCEL_EXTENSIONS:
        return "excel"
    else:
        return "unknown"


def ensure_directories_exist():
    """Ensure all required directories exist."""
    for directory in [UPLOADED_FILE_PATH, PARSED_FILE_PATH, GENERATED_QUESTIONS_PATH]:
        create_directory(directory) 