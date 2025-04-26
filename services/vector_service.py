"""
Vector embedding and search service for the Legal AI application.

This module handles document embedding, vector database operations,
and semantic search functionality.
"""

import json
import logging
import requests
from typing import List, Dict, Any, Optional

from sentence_transformers import SentenceTransformer
from database.db_utils import get_user
# Configure logging


from config import (
    DB_CONFIG, 
)
logger = logging.getLogger(__name__)


class VectorServiceError(Exception):
    """Custom exception for vector service errors."""
    pass


class VectorService:
    """Service for handling vector embeddings and search operations."""
    
    def __init__(self, qdrant_url: str, api_key: str, collection_name: str, 
                 model_name: str = "jinaai/jina-embeddings-v2-base-es"):
        """
        Initialize the vector service.
        
        Args:
            qdrant_url: URL of the Qdrant vector database
            api_key: API key for Qdrant
            collection_name: Name of the collection to use
            model_name: Name of the sentence transformer model for embeddings
        """
        self.qdrant_url = qdrant_url
        self.api_key = api_key
        self.collection_name = collection_name
        self.model = SentenceTransformer(model_name)
        self.headers = {
            "Content-Type": "application/json",
            "api-key": api_key
        }
    
    def encode_text(self, texts: List[str]) -> List[List[float]]:
        """
        Generate vector embeddings for a list of text chunks.
        
        Args:
            texts: List of text chunks to encode
            
        Returns:
            List of vector embeddings
        """
        try:
            return self.model.encode(texts)
        except Exception as e:
            logger.error(f"Error encoding text: {e}")
            raise VectorServiceError(f"Failed to encode text: {e}")
    
    def ensure_collection_exists(self) -> None:
        """
        Ensure the collection exists in Qdrant, creating it if necessary.
        
        Raises:
            VectorServiceError: If collection creation fails
        """
        try:
            # Check if collection exists
            response = requests.get(
                f"{self.qdrant_url}/collections/{self.collection_name}", 
                headers=self.headers
            )
            
            # If not, create it
            if response.status_code != 200:
                # Get vector size from the model
                sample_vector = self.model.encode(["Sample text"])
                vector_size = len(sample_vector[0])
                
                create_payload = {
                    "vectors": {"size": vector_size, "distance": "Cosine"}
                }
                
                create_response = requests.put(
                    f"{self.qdrant_url}/collections/{self.collection_name}", 
                    headers=self.headers, 
                    json=create_payload
                )
                
                if create_response.status_code != 200:
                    raise VectorServiceError(
                        f"Failed to create collection: {create_response.json()}"
                    )
                
                logger.info(f"Created collection '{self.collection_name}' in Qdrant")
            
        except Exception as e:
            logger.error(f"Error ensuring collection exists: {e}")
            raise VectorServiceError(f"Failed to ensure collection exists: {e}")
    
    def store_document_vectors(self, chunks: List[str], file_id: int,case_type:str) -> None:
        """
        Store document chunks as vectors in Qdrant.
        
        Args:
            chunks: List of text chunks from the document
            file_id: Unique identifier for the file
            
        Raises:
            VectorServiceError: If vector storage fails
        """
        try:
            # Ensure collection exists
            self.ensure_collection_exists()
            
            # Generate vectors for chunks
            vectors = self.encode_text(chunks)
            
            # Prepare points for Qdrant
            points = [
                {
                    "id": file_id * 1000 + i,
                    "vector": vec.tolist(),
                    "payload": {
                        "text": chunks[i],
                        "file_id": file_id,
                        "case_type": case_type
                    }
                }
                for i, vec in enumerate(vectors)
            ]
            
            # Store vectors in Qdrant
            upsert_response = requests.put(
                f"{self.qdrant_url}/collections/{self.collection_name}/points?wait=true",
                headers=self.headers,
                json={"points": points}
            )
            
            if upsert_response.status_code != 200:
                raise VectorServiceError(
                    f"Failed to upsert points: {upsert_response.json()}"
                )
            
            logger.info(f"Stored {len(points)} vectors for file_id {file_id} in Qdrant")
            
        except Exception as e:
            logger.error(f"Error storing document vectors: {e}")
            raise VectorServiceError(f"Failed to store document vectors: {e}")
    
    def search(self, query: str, auth_id: str, case_types: List[str] = None, limit: int = 6) -> List[Dict[str, Any]]:
        try:
            query_vector = self.encode_text([query])[0].tolist()
            context_ids = None
            initial_results = []

            if auth_id:
                context_ids = get_user(DB_CONFIG["url"], auth_id)[5]

                # Build base filter with context IDs
                filter_conditions = [{"has_id": context_ids}]

                # Add case_type filter if specified
                if case_types:
                    if len(case_types) == 1:
                        filter_conditions.append({
                            "key": "case_type",
                            "match": {"value": case_types[0]}
                        })
                    else:
                        filter_conditions.append({
                            "should": [
                                {"key": "case_type", "match": {"value": ct}}
                                for ct in case_types
                            ]
                        })

                payload = {
                    "vector": query_vector,
                    "filter": {"must": filter_conditions},
                    "limit": 6,
                    "with_payload": True,
                    "with_vector": False
                }

                response = requests.post(
                    f"{self.qdrant_url}/collections/{self.collection_name}/points/search",
                    headers=self.headers,
                    json=payload
                )

                if response.status_code != 200:
                    raise VectorServiceError(f"Search (context) failed: {response.json()}")
                
                initial_results = response.json().get("result", [])
                good_results = [r for r in initial_results if r["score"] >= 0.5]
                
                if len(good_results) >= 3:
                    print("Found good results in context search.")
                    return good_results

            # Fallback search (same case_type logic applies)
            fallback_payload = {
                "vector": query_vector,
                "limit": limit,
                "with_payload": True
            }

            if case_types:
                if len(case_types) == 1:
                    fallback_payload["filter"] = {
                        "must": [{"key": "case_type", "match": {"value": case_types[0]}}]
                    }
                else:
                    fallback_payload["filter"] = {
                        "should": [
                            {"key": "case_type", "match": {"value": ct}}
                            for ct in case_types
                        ]
                    }

            fallback_response = requests.post(
                f"{self.qdrant_url}/collections/{self.collection_name}/points/search",
                headers=self.headers,
                json=fallback_payload
            )

            if fallback_response.status_code != 200:
                raise VectorServiceError(f"Fallback search failed: {fallback_response.json()}")
            
            print("Fallback search executed.")
            return fallback_response.json().get("result", [])

        except Exception as e:
            logger.error(f"Error searching: {e}")
            raise VectorServiceError(f"Search failed: {e}")