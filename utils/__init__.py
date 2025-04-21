"""
Utilities package for the Legal AI application.

This package provides utility functions for file handling and logging.
"""

from utils.file_utils import get_file_stream, get_file_extension, validate_file_type
from utils.logging_utils import setup_logging

__all__ = [
    'get_file_stream',
    'get_file_extension',
    'validate_file_type',
    'setup_logging'
]