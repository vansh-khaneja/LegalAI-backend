"""
Cloudinary service for the Legal AI application.

This module handles file storage operations using Cloudinary.
"""

import logging
import cloudinary
import cloudinary.uploader
from typing import Dict, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)


class CloudinaryError(Exception):
    """Custom exception for Cloudinary service errors."""
    pass


class CloudinaryService:
    """Service for handling file storage operations with Cloudinary."""
    
    def __init__(self, cloud_name: str, api_key: str, api_secret: str):
        """
        Initialize the Cloudinary service.
        
        Args:
            cloud_name: Cloudinary cloud name
            api_key: Cloudinary API key
            api_secret: Cloudinary API secret
        """
        try:
            cloudinary.config(
                cloud_name=cloud_name,
                api_key=api_key,
                api_secret=api_secret
            )
            logger.info("Cloudinary service initialized")
        except Exception as e:
            logger.error(f"Error initializing Cloudinary service: {e}")
            raise CloudinaryError(f"Failed to initialize Cloudinary service: {e}")
    
    def upload_file(self, file_path: str, folder: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload a file to Cloudinary.
        
        Args:
            file_path: Path to the file to upload
            folder: Optional folder to store the file in
            
        Returns:
            Dictionary containing upload response data
            
        Raises:
            CloudinaryError: If file upload fails
        """
        try:
            # Prepare upload options
            options = {"resource_type": "raw"}
            if folder:
                options["folder"] = folder
            
            # Upload the file
            response = cloudinary.uploader.upload(file_path, **options)
            
            logger.info(f"File uploaded to Cloudinary: {response.get('secure_url')}")
            return response
            
        except Exception as e:
            logger.error(f"Error uploading file to Cloudinary: {e}")
            raise CloudinaryError(f"Failed to upload file: {e}")
    
    def delete_file(self, public_id: str) -> Dict[str, Any]:
        """
        Delete a file from Cloudinary.
        
        Args:
            public_id: Public ID of the file to delete
            
        Returns:
            Dictionary containing deletion response data
            
        Raises:
            CloudinaryError: If file deletion fails
        """
        try:
            response = cloudinary.uploader.destroy(public_id, resource_type="raw")
            
            logger.info(f"File deleted from Cloudinary: {public_id}")
            return response
            
        except Exception as e:
            logger.error(f"Error deleting file from Cloudinary: {e}")
            raise CloudinaryError(f"Failed to delete file: {e}")
    
    def generate_url(self, public_id: str) -> str:
        """
        Generate a URL for a file in Cloudinary.
        
        Args:
            public_id: Public ID of the file
            
        Returns:
            URL to access the file
        """
        try:
            url = cloudinary.CloudinaryImage(public_id).build_url(resource_type="raw")
            return url
        except Exception as e:
            logger.error(f"Error generating URL for file: {e}")
            raise CloudinaryError(f"Failed to generate URL: {e}")