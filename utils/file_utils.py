"""
File utility functions for the Legal AI application (FastAPI Version).

This module provides utility functions for file handling operations.
"""

import os
import logging
import io
from typing import Tuple, List, Optional, BinaryIO, Union
from fastapi import UploadFile

# Configure logging
logger = logging.getLogger(__name__)


class FileUtilsError(Exception):
    """Custom exception for file utility errors."""
    pass


def get_file_extension(filename: str) -> str:
    """
    Get the file extension from a filename.
    
    Args:
        filename: Name of the file
        
    Returns:
        File extension (lowercase) including the period
    """
    return os.path.splitext(filename)[1].lower()


async def get_file_stream(file: UploadFile) -> Tuple[BinaryIO, str]:
    """
    Get a file stream from an uploaded file without saving it locally.
    
    Args:
        file: Uploaded file object
        
    Returns:
        Tuple of (file stream, filename)
        
    Raises:
        FileUtilsError: If file processing fails
    """
    try:
        # Read the file data into memory asynchronously
        file_data = await file.read()
        
        # Create a BytesIO object from the file data
        file_stream = io.BytesIO(file_data)
        
        # Get the original filename
        original_filename = file.filename
        
        # Reset the file stream position to the beginning
        file_stream.seek(0)
        
        logger.info(f"File '{original_filename}' loaded into memory")
        return file_stream, original_filename
        
    except Exception as e:
        logger.error(f"Error processing uploaded file: {e}")
        raise FileUtilsError(f"Failed to process uploaded file: {e}")


def validate_file_type(filename: str, allowed_extensions: List[str]) -> bool:
    """
    Validate if a file has an allowed extension.
    
    Args:
        filename: Name of the file
        allowed_extensions: List of allowed extensions (with period)
        
    Returns:
        True if file extension is allowed, False otherwise
    """
    extension = get_file_extension(filename)
    return extension in allowed_extensions