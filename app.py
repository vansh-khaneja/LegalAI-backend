"""
Legal AI Application - Main Entry Point

This is the main entry point for the Legal AI application.
It initializes the Flask application and registers the API routes.
"""

import os
from flask import Flask
from flask_cors import CORS

from config import FLASK_CONFIG
from utils.logging_utils import setup_logging
from api.routes import register_routes


def create_app() -> Flask:
    """
    Create and configure the Flask application.
    
    Returns:
        Configured Flask application instance
    """
    # Set up logging
    setup_logging(log_level="INFO", log_file="logs/legalai.log")
    
    # Create Flask application
    app = Flask(__name__)
    
    # Enable CORS
    CORS(app)
    
    # Register API routes
    register_routes(app)
    
    return app


# Application entry point
if __name__ == "__main__":
    app = create_app()
    app.run(
        debug=FLASK_CONFIG["debug"],
        port=FLASK_CONFIG["port"]
    )