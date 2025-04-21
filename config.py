"""
Configuration module for the Legal AI application.

This module handles loading environment variables and provides configuration
settings for the application components.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database configuration
DB_CONFIG = {
    "url": os.getenv("DB_URL"),
}

# Vector store configuration
VECTOR_CONFIG = {
    "qdrant_url": os.getenv("QDRANT_URL"),
    "api_key": os.getenv("API_KEY"),
    "collection_name": os.getenv("COLLECTION_NAME"),
    "model_name": "jinaai/jina-embeddings-v2-base-es",
    "chunk_size": 2050,
    "chunk_overlap": 150
}

# Cloudinary configuration
CLOUDINARY_CONFIG = {
    "cloud_name": os.getenv("CLOUD_NAME"),
    "api_key": os.getenv("CLOUD_KEY"),
    "api_secret": os.getenv("CLOUD_SECRET")
}

# LLM configuration
LLM_CONFIG = {
    "groq_api_key": os.getenv("GROQ_API"),
    "model_name": "llama3-8b-8192"
}

# Request headers
HEADERS = {
    "Content-Type": "application/json",
    "api-key": VECTOR_CONFIG["api_key"]
}

# Flask configuration
FLASK_CONFIG = {
    "debug": True,
    "port": 5000
}