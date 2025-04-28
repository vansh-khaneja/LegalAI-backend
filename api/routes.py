"""
API routes for the Legal AI application (FastAPI Version).

This module defines the API routes for document upload and retrieval.
"""

import os
import random
import json
import logging
import io
from typing import Dict, Any, List, Optional, Union

from fastapi import FastAPI, File, UploadFile, Form, Body, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

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


# Define Pydantic models for request/response data

class SuccessResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: Dict[str, Any]


class SearchQuery(BaseModel):
    question: str
    categories: Optional[List[str]] = None
    auth_id: Optional[str] = None


class MetadataItem(BaseModel):
    file_id: int
    id: Optional[int] = None
    file_url: Optional[str] = None
    file_summary: Optional[str] = None
    case_type: Optional[str] = None
    score: Optional[float] = None
    text: Optional[str] = None
    date: Optional[str] = None


class SearchResponse(BaseModel):
    answer: str
    metadata: List[MetadataItem] = []


class UserRequest(BaseModel):
    auth_id: str


class UpdateUserRequest(BaseModel):
    auth_id: str
    chat_history: Optional[str] = None
    is_premium: Optional[bool] = None


class ContextRequest(BaseModel):
    auth_id: str
    context: Union[str, List[int]]


class ChatMessageRequest(BaseModel):
    auth_id: str
    session_id: Optional[str] = ""
    sender: str
    message: str


class SessionRequest(BaseModel):
    auth_id: str
    session_id: Optional[str] = None


# Configure logging
logger = logging.getLogger(__name__)


def register_routes(app: FastAPI) -> None:
    """
    Register API routes with the FastAPI application.
    
    Args:
        app: FastAPI application instance
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
    @app.post("/upload", response_model=SuccessResponse)
    async def upload_file(
        file: UploadFile = File(...),
        caseType: str = Form("unknown"),
        date: str = Form("unknown")
    ):
        """
        Handle document upload and processing.
        
        Returns:
            JSON response with upload result
        """
        try:
            # Validate file type
            if not validate_file_type(file.filename, [".pdf", ".docx"]):
                raise HTTPException(
                    status_code=400,
                    detail="Unsupported file type. Only PDF and DOCX are allowed."
                )
            
            # Get file stream instead of saving to disk
            file_stream, original_filename = await get_file_stream(file)
            
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
            vector_service.store_document_vectors(chunks, file_id, caseType, date)
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
                case_type=caseType
            )
            logger.info(f"Added entry to database with file_id: {file_id}")
            
            # Close the file stream
            file_stream.close()
            
            return SuccessResponse(
                message=f"File processed and uploaded as {caseType} case",
                data={"file_id": file_id}
            )
            
        except Exception as e:
            logger.error(f"Error in upload_file: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")
    
    # Query retrieval route
    @app.post("/retrieve", response_model=SuccessResponse)
    async def search_query(query: SearchQuery):
        """
        Handle search queries and generate responses.
        
        Returns:
            JSON response with search results and answer
        """
        try:
            question = query.question
            categories = query.categories
            auth_id = query.auth_id
            
            if not question:
                raise HTTPException(status_code=400, detail="No question provided")
                
            logger.info(f"Received question: {question}")
            logger.info(f"Categories filter: {categories}")
            
            # Route query to appropriate service
            query_type = llm_service.route_query(question)
            logger.info(f"Query routed to: {query_type}")
            
            # Handle general queries
            if query_type == "general":
                answer = llm_service.general_response(question)
                return SuccessResponse(data=SearchResponse(
                    answer=answer,
                    metadata=[]
                ))
            
            # Handle case-based queries
            else:
                # Generate query vector and search
                search_results = vector_service.search(question, auth_id, case_types=categories, limit=6)
                
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
                    date = payload.get("date")
                    
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
                        
                        file_metadata[file_id] = MetadataItem(
                            file_id=file_id,
                            id=id,
                            score=score,
                            text=text,
                            file_url=data.get("file_url"),
                            file_summary=data.get("file_summary"),
                            case_type=data.get("case_type"),
                            date=date,
                        )
                    
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
                
                return SuccessResponse(data=SearchResponse(
                    answer=answer,
                    metadata=metadata_list
                ))
                
        except Exception as e:
            logger.error(f"Error in search_query: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to process query: {str(e)}")
    
    # Add user if not exist
    @app.post("/add_user", response_model=SuccessResponse)
    async def add_user(user: UserRequest):
        """
        Handle user addition.
        
        Returns:
            JSON response with user addition result
        """
        try:
            auth_id = user.auth_id
            
            if not auth_id:
                raise HTTPException(status_code=400, detail="auth_id required")
            
            # Add user to database
            create_default_user(
                db_url=DB_CONFIG["url"],
                auth_id=auth_id
            )
            
            return SuccessResponse(message="User added successfully")
            
        except Exception as e:
            logger.error(f"Error in add_user: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to add user: {str(e)}")

    # Update user fields
    @app.post("/update_user_fields", response_model=SuccessResponse)
    async def update_user(user_data: UpdateUserRequest):
        """
        Handle user field updates.
        
        Returns:
            JSON response with user update result
        """
        try:
            auth_id = user_data.auth_id
            is_history = user_data.chat_history
            is_premium = user_data.is_premium
            
            if is_history is None and is_premium is None:
                raise HTTPException(status_code=400, detail="history or isPremium required")
            
            # Update user fields in database
            update_user_fields(
                db_url=DB_CONFIG["url"],
                auth_id=auth_id,
                chat_history=is_history,
                is_premium=is_premium
            )
            
            return SuccessResponse(message="User fields updated successfully")
            
        except Exception as e:
            logger.error(f"Error in update_user_fields: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to update user fields: {str(e)}")
    
    # Get user information
    @app.post("/get_user", response_model=SuccessResponse)
    async def get_user_info(user: UserRequest):
        """
        Handle user information retrieval.
        
        Returns:
            JSON response with user information
        """
        try:
            auth_id = user.auth_id
            
            if not auth_id:
                raise HTTPException(status_code=400, detail="auth_id required")
            
            # Retrieve user information from database
            user_info = get_user(
                db_url=DB_CONFIG["url"],
                auth_id=auth_id
            )
            
            return SuccessResponse(data=user_info)
            
        except Exception as e:
            logger.error(f"Error in get_user: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve user: {str(e)}")
    
    # Append context history
    @app.post("/append_context_history", response_model=SuccessResponse)
    async def append_context(context_data: ContextRequest):
        """
        Handle context history appending.
        
        Returns:
            JSON response with context history append result
        """
        try:
            auth_id = context_data.auth_id
            context = context_data.context
            
            if not auth_id or not context:
                raise HTTPException(status_code=400, detail="auth_id and context required")
            
            # Append context history in database
            append_to_context_history_queue(
                db_url=DB_CONFIG["url"],
                auth_id=auth_id,
                new_values=context
            )
            
            return SuccessResponse(message="Context appended successfully")
            
        except Exception as e:
            logger.error(f"Error in append_context_history: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to append context: {str(e)}")
    
    # Add chat message
    @app.post("/add_chat_message", response_model=SuccessResponse)
    async def add_chat_message_route(message_data: ChatMessageRequest):
        """
        Handle chat message addition.
        
        Returns:
            JSON response with chat message addition result
        """
        try:
            auth_id = message_data.auth_id
            session_id = message_data.session_id
            sender = message_data.sender
            message = message_data.message
            
            if not auth_id or not message:
                raise HTTPException(status_code=400, detail="auth_id and message required")
            
            # Add chat message in database
            add_chat_message(
                db_url=DB_CONFIG["url"],
                auth_id=auth_id,
                session_id=session_id,
                sender=sender,
                message=message
            )
            
            return SuccessResponse(message="Chat message added successfully")
            
        except Exception as e:
            logger.error(f"Error in add_chat_message: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to add chat message: {str(e)}")
    
    # Get chat history
    @app.post("/get_chat_history", response_model=SuccessResponse)
    async def get_chat_history_route(session_data: SessionRequest):
        """
        Handle chat history retrieval.
        
        Returns:
            JSON response with chat history
        """
        try:
            auth_id = session_data.auth_id
            session_id = session_data.session_id
            
            if not auth_id:
                raise HTTPException(status_code=400, detail="auth_id required")
            
            # Retrieve chat history from database
            chat_history = get_chat_history(
                db_url=DB_CONFIG["url"],
                auth_id=auth_id,
                session_id=session_id
            )
            
            return SuccessResponse(data=chat_history)
            
        except Exception as e:
            logger.error(f"Error in get_chat_history: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve chat history: {str(e)}")
    
    # Get unique session IDs
    @app.post("/get_unique_session_ids", response_model=SuccessResponse)
    async def get_unique_session_ids_route(user: UserRequest):
        """
        Handle unique session ID retrieval.
        
        Returns:
            JSON response with unique session IDs
        """
        try:
            auth_id = user.auth_id
            
            if not auth_id:
                raise HTTPException(status_code=400, detail="auth_id required")
            
            # Retrieve unique session IDs from database
            session_ids = get_unique_session_ids(
                db_url=DB_CONFIG["url"],
                auth_id=auth_id
            )
            
            return SuccessResponse(data=session_ids)
            
        except Exception as e:
            logger.error(f"Error in get_unique_session_ids: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve unique session IDs: {str(e)}")