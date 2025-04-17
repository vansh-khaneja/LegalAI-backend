"""
API response formatters for the Legal AI application.

This module provides standardized response formatters for API endpoints.
"""

from typing import Dict, Any, Optional, Union, List
from flask import jsonify


def success_response(data: Any = None, message: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a success response.
    
    Args:
        data: Response data
        message: Optional success message
        
    Returns:
        JSON response with data and success status
    """
    response = {
        "success": True,
        "data": data
    }
    
    if message:
        response["message"] = message
        
    return jsonify(response), 200


def error_response(message: str, status_code: int = 400, error_code: Optional[str] = None) -> Dict[str, Any]:
    """
    Create an error response.
    
    Args:
        message: Error message
        status_code: HTTP status code
        error_code: Optional application-specific error code
        
    Returns:
        JSON response with error details
    """
    response = {
        "success": False,
        "error": {
            "message": message
        }
    }
    
    if error_code:
        response["error"]["code"] = error_code
        
    return jsonify(response), status_code


def not_found_response(resource_type: str, identifier: Optional[Any] = None) -> Dict[str, Any]:
    """
    Create a not found (404) response.
    
    Args:
        resource_type: Type of resource that was not found
        identifier: Optional identifier that was used to look up the resource
        
    Returns:
        JSON response with not found error
    """
    message = f"{resource_type} not found"
    if identifier:
        message += f" for identifier: {identifier}"
        
    return error_response(message, status_code=404, error_code="resource_not_found")


def bad_request_response(message: str = "Invalid request") -> Dict[str, Any]:
    """
    Create a bad request (400) response.
    
    Args:
        message: Error message
        
    Returns:
        JSON response with bad request error
    """
    return error_response(message, status_code=400, error_code="bad_request")


def server_error_response(message: str = "Internal server error") -> Dict[str, Any]:
    """
    Create a server error (500) response.
    
    Args:
        message: Error message
        
    Returns:
        JSON response with server error
    """
    return error_response(message, status_code=500, error_code="server_error")