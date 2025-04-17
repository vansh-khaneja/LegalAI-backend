"""
File utility functions for the Legal AI application.

This module provides utility functions for file handling operations.
"""

import os
import logging
from typing import Tuple, List, Optional
from werkzeug.datastructures import FileStorage

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


def save_uploaded_file(file: FileStorage, upload_folder: str) -> str:
    """
    Save an uploaded file to the specified folder.
    
    Args:
        file: Uploaded file object
        upload_folder: Folder to save the file in
        
    Returns:
        Path to the saved file
        
    Raises:
        FileUtilsError: If file saving fails
    """
    try:
        # Ensure upload folder exists
        os.makedirs(upload_folder, exist_ok=True)
        
        # Generate file path
        file_path = os.path.join(upload_folder, file.filename)
        
        # Save the file
        file.save(file_path)
        
        logger.info(f"File saved to {file_path}")
        return file_path
        
    except Exception as e:
        logger.error(f"Error saving uploaded file: {e}")
        raise FileUtilsError(f"Failed to save uploaded file: {e}")


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


def generate_unique_filename(filename: str, upload_folder: str) -> str:
    """
    Generate a unique filename for an uploaded file to avoid overwriting.
    
    Args:
        filename: Original filename
        upload_folder: Folder where the file will be saved
        
    Returns:
        Unique filename
    """
    base, extension = os.path.splitext(filename)
    counter = 1
    new_filename = filename
    
    # Check if file already exists and generate unique name
    while os.path.exists(os.path.join(upload_folder, new_filename)):
        new_filename = f"{base}_{counter}{extension}"
        counter += 1
    
    return new_filename