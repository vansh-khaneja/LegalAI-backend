"""
Utilities package for the Legal AI application.

This package provides utility functions for file handling and logging.
"""

from utils.file_utils import save_uploaded_file, get_file_extension
from utils.logging_utils import setup_logging

__all__ = [
    'save_uploaded_file',
    'get_file_extension',
    'setup_logging'
]