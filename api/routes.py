"""
API routes for the Legal AI application.

This module defines the API routes for document upload and retrieval.
"""

import os
import random
import json
import logging
from typing import Dict, Any, List, Optional

from flask import Flask, request, jsonify, Response

from config import (
    DB_CONFIG, 
    VECTOR_CONFIG, 
    CLOUDINARY_CONFIG, 
    LLM_CONFIG,
    UPLOAD_FOLDER
)

from utils.file_utils import (
    save_uploaded_file,
    validate_file_type
)

from services.document_service import process_document
from services.vector_service import VectorService
from services.cloudinary_service import CloudinaryService
from services.llm_service import LLMService

from database.db_utils import (
    init_database,
    add_entry,
    get_data_by_file_id
)

from api.responses import (
    success_response,
    error_response,
    bad_request_response
)

# Configure logging
logger = logging.getLogger(__name__)


def register_routes(app: Flask) -> None:
    """
    Register API routes with the Flask application.
    
    Args:
        app: Flask application instance
    """
    # Initialize services
    vector_service = VectorService(
        qdrant_url=VECTOR_CONFIG["qdrant_url"],
        api_key=VECTOR_CONFIG["api_key"],
        collection_name=VECTOR_CONFIG["collection_name"],
        model_name=VECTOR_CONFIG["model_name"]
    )
    
    cloudinary_service = CloudinaryService(
        cloud_name=CLOUDINARY_CONFIG["cloud_name"],
        api_key=CLOUDINARY_CONFIG["api_key"],
        api_secret=CLOUDINARY_CONFIG["api_secret"]
    )
    
    llm_service = LLMService(
        groq_api_key=LLM_CONFIG["groq_api_key"],
        model_name=LLM_CONFIG["model_name"]
    )
    
    # Initialize database
    init_database(DB_CONFIG["url"])
    
    # Document upload route
    @app.route("/upload", methods=["POST"])
    def upload_file() -> Response:
        """
        Handle document upload and processing.
        
        Returns:
            JSON response with upload result
        """
        try:
            # Check if file was provided
            if 'file' not in request.files:
                return bad_request_response("No file part")
            
            file = request.files['file']
            if file.filename == '':
                return bad_request_response("No selected file")
            
            # Get case type from request
            case_type = request.form.get("caseType", "unknown")
            logger.info(f"Received case type: {case_type}")
            
            # Validate file type
            if not validate_file_type(file.filename, [".pdf", ".docx"]):
                return bad_request_response("Unsupported file type. Only PDF and DOCX are allowed.")
            
            # Save uploaded file
            file_path = save_uploaded_file(file, UPLOAD_FOLDER)
            
            # Upload to Cloudinary
            response = cloudinary_service.upload_file(file_path)
            file_url = response['secure_url']
            logger.info(f"File uploaded to Cloudinary: {file_url}")
            
            # Process document
            chunks = process_document(
                file_path, 
                chunk_size=VECTOR_CONFIG["chunk_size"],
                chunk_overlap=VECTOR_CONFIG["chunk_overlap"]
            )
            
            # Generate a random file ID
            file_id = random.randint(10000, 99999)
            
            # Store document vectors
            vector_service.store_document_vectors(chunks, file_id)
            logger.info(f"Stored vectors for file_id {file_id}")
            
            # Add entry to database
            add_entry(
                db_url=DB_CONFIG["url"],
                file_id=file_id,
                file_url=file_url,
                file_summary="This is a test summary",  # TODO: Generate real summary
                case_type=case_type
            )
            logger.info(f"Added entry to database with file_id: {file_id}")
            
            return success_response(
                message=f"File processed and uploaded as {case_type} case",
                data={"file_id": file_id}
            )
            
        except Exception as e:
            logger.error(f"Error in upload_file: {e}")
            return error_response(f"Failed to process file: {str(e)}", 500)
    
    # Query retrieval route
    @app.route("/retrieve", methods=["POST"])
    def search_query() -> Response:
        """
        Handle search queries and generate responses.
        
        Returns:
            JSON response with search results and answer
        """
        try:
            # Get query from request
            data = request.get_json()
            question = data.get("question", "")
            
            if not question:
                return bad_request_response("No question provided")
                
            logger.info(f"Received question: {question}")
            
            # Route query to appropriate service
            query_type = llm_service.route_query(question)
            logger.info(f"Query routed to: {query_type}")
            
            # Handle general queries
            if query_type == "general":
                answer = llm_service.general_response(question)
                return success_response({
                    "answer": answer,
                    "metadata": []
                })
            
            # Handle case-based queries
            else:
                # Generate query vector and search
                search_results = vector_service.search(question, limit=6)
                
                # Build context from search results
                context = ""
                file_metadata = {}
                metadata_list = []
                
                for i, result in enumerate(search_results):
                    payload = result["payload"]
                    file_id = payload.get("file_id")
                    text = payload.get("text")
                    score = result.get("score")
                    
                    context += f"{i}Text: {text}\n"
                    
                    if file_id not in file_metadata:
                        data_json = get_data_by_file_id(DB_CONFIG["url"], file_id)
                        try:
                            data = json.loads(data_json)
                            print(data)
                        except Exception:
                            data = {}
                        
                        file_metadata[file_id] = {
                            "file_id": file_id,
                            "score": score,
                            "text": text,
                            "file_url": data.get("file_url"),
                            "file_summary": data.get("file_summary"),
                            "case_type": data.get("case_type")
                        }
                    
                    metadata_list.append(file_metadata[file_id])
                
                # Generate response
                answer = llm_service.case_based_response(question, context)
                
                return success_response({
                    "answer": answer,
                    "metadata": metadata_list
                })
                
        except Exception as e:
            logger.error(f"Error in search_query: {e}")
            return error_response(f"Failed to process query: {str(e)}", 500)