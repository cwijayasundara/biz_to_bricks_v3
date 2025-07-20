"""
Utility functions for the Document Processing API.
"""

from .file_utils import (
    get_file_path,
    is_excel_or_csv_file,
    get_file_type,
    ensure_directories_exist
)

from .search_utils import compare_and_rerank_results

__all__ = [
    "get_file_path",
    "is_excel_or_csv_file", 
    "get_file_type",
    "ensure_directories_exist",
    "compare_and_rerank_results"
] 