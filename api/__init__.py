"""
API package for the Legal AI application.

This package provides API routes and response formatters.
"""

from api.routes import register_routes
from api.responses import (
    success_response, 
    error_response,
    not_found_response, 
    bad_request_response,
    server_error_response
)

__all__ = [
    'register_routes',
    'success_response',
    'error_response',
    'not_found_response',
    'bad_request_response',
    'server_error_response'
]