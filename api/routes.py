"""
API routes for the Legal AI application.

This module defines the API routes for document upload and retrieval.
"""

import os
import random
import json
import logging
import io
from typing import Dict, Any, List, Optional

from flask import Flask, request, jsonify, Response

from config import (
    DB_CONFIG, 
    VECTOR_CONFIG, 
    CLOUDINARY_CONFIG, 
    LLM_CONFIG
)

from utils.file_utils import (
    get_file_stream,
    validate_file_type
)

from services.document_service import process_document_from_stream
from services.vector_service import VectorService
from services.cloudinary_service import CloudinaryService
from services.llm_service import LLMService
from services.summary_service import SummarizationService

from database.db_utils import (
    init_database,
    add_entry,
    get_data_by_file_id,
    create_default_user,
    update_user_fields,
    get_user,
    append_to_context_history_queue,
    add_chat_message,
    get_chat_history,
    get_unique_session_ids
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

    summarization_service = SummarizationService(
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
            
            # Get file stream instead of saving to disk
            file_stream, original_filename = get_file_stream(file)
            
            # Process document directly from stream
            chunks = process_document_from_stream(
                file_stream=file_stream,
                file_name=original_filename,
                chunk_size=VECTOR_CONFIG["chunk_size"],
                chunk_overlap=VECTOR_CONFIG["chunk_overlap"]
            )
            
            # Generate a random file ID
            file_id = random.randint(10000, 99999)
            
            # Store document vectors
            vector_service.store_document_vectors(chunks, file_id,case_type)
            logger.info(f"Stored vectors for file_id {file_id}")
            
            # Reset stream position for summarization
            file_stream.seek(0)
            
            # Generate summary directly from stream
            summary = summarization_service.generate_summary_from_stream(
                file_stream=file_stream,
                file_name=original_filename
            )
            
            # Reset stream position for Cloudinary upload
            file_stream.seek(0)
            
            # Upload to Cloudinary directly from stream
            response = cloudinary_service.upload_file_stream(
                file_stream=file_stream,
                filename=original_filename
            )
            file_url = response['secure_url']
            logger.info(f"File uploaded to Cloudinary: {file_url}")
            
            # Add entry to database
            add_entry(
                db_url=DB_CONFIG["url"],
                file_id=file_id,
                file_url=file_url,
                file_summary=summary,
                case_type=case_type
            )
            logger.info(f"Added entry to database with file_id: {file_id}")
            
            # Close the file stream
            file_stream.close()
            
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
            # Get categories from request, defaults to None which will search all categories
            categories = data.get("categories", None)
            auth_id = data.get("auth_id", None)
            print(f"Auth ID: {auth_id}")
            print(f"Request data: {data}")
            
            if not question:
                return bad_request_response("No question provided")
                
            logger.info(f"Received question: {question}")
            logger.info(f"Categories filter: {categories}")
            
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
                search_results = vector_service.search(question,auth_id, case_types=categories, limit=6)
                
                # Build context from search results
                context = ""
                file_metadata = {}
                metadata_list = []
                
                # Track which file_ids have been added to metadata_list to avoid duplicates
                added_file_ids = set()
                
                for i, result in enumerate(search_results):
                    payload = result["payload"]
                    file_id = payload.get("file_id")
                    text = payload.get("text")
                    score = result.get("score")
                    id = result.get("id")
                    
                    context += f"{i}Text: {text}\n\n"  # Added extra newline for better separation
                    
                    # Only fetch and process metadata if we haven't seen this file_id before
                    if file_id not in file_metadata:
                        data_json = get_data_by_file_id(DB_CONFIG["url"], file_id)
                        try:
                            data = json.loads(data_json)
                            print(f"File metadata for ID {file_id}: {data}")
                        except Exception as e:
                            logger.error(f"Error parsing file metadata: {e}")
                            data = {}
                        
                        file_metadata[file_id] = {
                            "file_id": file_id,
                            "id":id,
                            "score": score,
                            "text": text,
                            "file_url": data.get("file_url"),
                            "file_summary": data.get("file_summary"),
                            "case_type": data.get("case_type"),
                            
                        }
                    
                    # Only add to metadata_list if this file_id hasn't been added yet
                    if file_id not in added_file_ids:
                        metadata_list.append(file_metadata[file_id])
                        added_file_ids.add(file_id)
                
                # Check if we found any results
                if not search_results:
                    logger.warning("No search results found for the query")
                    answer = "Lo siento, no pude encontrar información relevante para tu consulta."
                else:
                    # Generate response based on search results
                    answer = llm_service.case_based_response(question, context)
                
                return success_response({
                    "answer": answer,
                    "metadata": metadata_list
                })
                
        except Exception as e:
            logger.error(f"Error in search_query: {e}")
            return error_response(f"Failed to process query: {str(e)}", 500)
        

    
    #add user if not exist
    @app.route("/add_user", methods=["POST"])
    def add_user() -> Response:
        """
        Handle user addition.
        
        Returns:
            JSON response with user addition result
        """
        try:
            # Get user data from request
            data = request.get_json()
            auth_id = data.get("auth_id", "")
            
            if not auth_id:
                return bad_request_response("auth_id required")
            
            # Add user to database
            create_default_user(
                db_url=DB_CONFIG["url"],
                auth_id=auth_id
            )
            
            return success_response(message="User added successfully")
            
        except Exception as e:
            logger.error(f"Error in add_user: {e}")
            return error_response(f"Failed to add user: {str(e)}", 500)

    

    @app.route("/update_user_fields", methods=["POST"])
    def update_user() -> Response:
        """
        Handle user field updates.
        
        Returns:
            JSON response with user update result
        """
        try:
            # Get user data from request
            data = request.get_json()
            auth_id = data.get("auth_id", "")
            is_history = data.get("chat_history", None)
            is_premium = data.get("is_premium", None)
            
            if is_history==None and is_premium==None:
                return bad_request_response("history or isPremium required")
            
            # Update user fields in database
            if is_history!=None and is_premium!=None:
                update_user_fields(
                db_url=DB_CONFIG["url"],
                auth_id=auth_id,
                chat_history=is_history,
                is_premium=is_premium
            )
            
            if is_history!=None and is_premium==None:
                update_user_fields(
                db_url=DB_CONFIG["url"],
                auth_id=auth_id,
                chat_history=is_history
            )
                
            if is_history==None and is_premium!=None:
                update_user_fields(
                db_url=DB_CONFIG["url"],
                auth_id=auth_id,
                is_premium=is_premium
            )
            
            
            
            return success_response(message="User fields updated successfully")
            
        except Exception as e:
            logger.error(f"Error in update_user_fields: {e}")
            return error_response(f"Failed to update user fields: {str(e)}", 500)
        

    @app.route("/get_user", methods=["POST"])
    def get_user_info() -> Response:
        """
        Handle user information retrieval.
        
        Returns:
            JSON response with user information
        """
        try:
            # Get user data from request
            data = request.get_json()
            auth_id = data.get("auth_id", "")
            
            if not auth_id:
                return bad_request_response("auth_id required")
            
            # Retrieve user information from database
            user_info = get_user(
                db_url=DB_CONFIG["url"],
                auth_id=auth_id
            )
            
            return success_response(data=user_info)
            
        except Exception as e:
            logger.error(f"Error in get_user: {e}")
            return error_response(f"Failed to retrieve user: {str(e)}", 500)
        

    @app.route("/append_context_history", methods=["POST"])
    def append_context() -> Response:
        """
        Handle context history appending.
        
        Returns:
            JSON response with context history append result
        """
        try:
            # Get user data from request
            data = request.get_json()
            auth_id = data.get("auth_id", "")
            context = data.get("context", "")
            
            if not auth_id or not context:
                return bad_request_response("auth_id and context required")
            
            # Append context history in database
            append_to_context_history_queue(
                db_url=DB_CONFIG["url"],
                auth_id=auth_id,
                new_values=context
            )
            
            return success_response(message="Context appended successfully")
            
        except Exception as e:
            logger.error(f"Error in append_context_history: {e}")
            return error_response(f"Failed to append context: {str(e)}", 500)
    
    
    @app.route("/add_chat_message", methods=["POST"])
    def add_chat_message_route() -> Response:
        """
        Handle chat message addition.
        
        Returns:
            JSON response with chat message addition result
        """
        try:
            # Get user data from request
            data = request.get_json()
            auth_id = data.get("auth_id", "")
            session_id = data.get("session_id", "")
            sender = data.get("sender", "")
            message = data.get("message", "")
            
            if not auth_id or not message:
                return bad_request_response("auth_id and message required")
            
            # Add chat message in database
            add_chat_message(
                db_url=DB_CONFIG["url"],
                auth_id=auth_id,
                session_id=session_id,
                sender=sender,
                message=message
            )
            
            return success_response(message="Chat message added successfully")
            
        except Exception as e:
            logger.error(f"Error in add_chat_message: {e}")
            return error_response(f"Failed to add chat message: {str(e)}", 500)
        

    @app.route("/get_chat_history", methods=["POST"])
    def get_chat_history_route() -> Response:
        """
        Handle chat history retrieval.
        
        Returns:
            JSON response with chat history
        """
        try:
            # Get user data from request
            data = request.get_json()
            auth_id = data.get("auth_id", "")
            session_id = data.get("session_id", "")
            
            if not auth_id:
                return bad_request_response("auth_id required")
            
            # Retrieve chat history from database
            chat_history = get_chat_history(
                db_url=DB_CONFIG["url"],
                auth_id=auth_id,
                session_id=session_id
            )
            
            return success_response(data=chat_history)
            
        except Exception as e:
            logger.error(f"Error in get_chat_history: {e}")
            return error_response(f"Failed to retrieve chat history: {str(e)}", 500)
        
    @app.route("/get_unique_session_ids", methods=["POST"])
    def get_unique_session_ids_route() -> Response:
        """
        Handle unique session ID retrieval.
        
        Returns:
            JSON response with unique session IDs
        """
        try:
            # Get user data from request
            data = request.get_json()
            auth_id = data.get("auth_id", "")
            
            if not auth_id:
                return bad_request_response("auth_id required")
            
            # Retrieve unique session IDs from database
            session_ids = get_unique_session_ids(
                db_url=DB_CONFIG["url"],
                auth_id=auth_id
            )
            
            return success_response(data=session_ids)
            
        except Exception as e:
            logger.error(f"Error in get_unique_session_ids: {e}")
            return error_response(f"Failed to retrieve unique session IDs: {str(e)}", 500)