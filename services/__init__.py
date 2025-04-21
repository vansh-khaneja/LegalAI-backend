"""
Services package for the Legal AI application.

This package provides services for document processing, vector operations,
file storage, and language model interactions.
"""

from services.document_service import (
    load_document_from_stream,
    split_text,
    process_document_from_stream,
    DocumentProcessingError
)

from services.vector_service import (
    VectorService,
    VectorServiceError
)

from services.cloudinary_service import (
    CloudinaryService,
    CloudinaryError
)

from services.llm_service import (
    LLMService,
    LLMServiceError,
    RouteQuery
)

from services.summary_service import (
    SummarizationService,
    SummarizationError
)   

__all__ = [
    'load_document_from_stream',
    'split_text',
    'process_document_from_stream',
    'DocumentProcessingError',
    'VectorService',
    'VectorServiceError',
    'CloudinaryService',
    'CloudinaryError',
    'LLMService',
    'LLMServiceError',
    'RouteQuery',
    'SummarizationService',
    'SummarizationError'
]