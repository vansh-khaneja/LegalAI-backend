"""
Legal AI Application - Main Entry Point (FastAPI Version)

This is the main entry point for the Legal AI application.
It initializes the FastAPI application and registers the API routes.
"""

import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from config import FASTAPI_CONFIG
from utils.logging_utils import setup_logging
from api.routes import register_routes


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    # Set up logging
    setup_logging(log_level="INFO", log_file="logs/legalai.log")
    
    # Create FastAPI application
    app = FastAPI(
        title="Legal AI API",
        description="API for processing, analyzing, and retrieving information from legal documents",
        version="1.0.0"
    )
    
    # Enable CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Adjust for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Register API routes
    register_routes(app)
    
    return app


# Create FastAPI application instance
app = create_app()


# Run with uvicorn if executed directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=FASTAPI_CONFIG["host"],
        port=FASTAPI_CONFIG["port"],
        reload=FASTAPI_CONFIG["reload"]
    )