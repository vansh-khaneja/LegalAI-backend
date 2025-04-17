"""
Document processing service for the Legal AI application.

This module handles document loading, parsing, and text extraction
from various file formats.
"""

import os
import logging
from typing import List, Optional, Dict, Any

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from docx import Document

# Configure logging
logger = logging.getLogger(__name__)


class DocumentProcessingError(Exception):
    """Custom exception for document processing errors."""
    pass


def load_document(file_path: str) -> str:
    """
    Load a document from the given file path and extract its text content.
    
    Args:
        file_path: Path to the document file
        
    Returns:
        Extracted text content from the document
        
    Raises:
        DocumentProcessingError: If document loading or text extraction fails
    """
    try:
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == ".pdf":
            return _load_pdf(file_path)
        elif file_ext == ".docx":
            return _load_docx(file_path)
        else:
            raise DocumentProcessingError(f"Unsupported file type: {file_ext}. Only PDF and DOCX are supported.")
    
    except Exception as e:
        logger.error(f"Error loading document {file_path}: {e}")
        raise DocumentProcessingError(f"Failed to load document: {e}")


def _load_pdf(file_path: str) -> str:
    """
    Load and extract text from a PDF file.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Extracted text content from the PDF
    """
    loader = PyPDFLoader(file_path)
    docs = loader.load()
    return "\n".join([doc.page_content for doc in docs])


def _load_docx(file_path: str) -> str:
    """
    Load and extract text from a DOCX file.
    
    Args:
        file_path: Path to the DOCX file
        
    Returns:
        Extracted text content from the DOCX
    """
    doc = Document(file_path)
    full_text = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            full_text.append(text)
    return "\n".join(full_text)


def split_text(text: str, chunk_size: int = 2050, chunk_overlap: int = 150) -> List[str]:
    """
    Split text into chunks for processing.
    
    Args:
        text: Text content to split
        chunk_size: Maximum size of each chunk
        chunk_overlap: Overlap between consecutive chunks
        
    Returns:
        List of text chunks
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    return splitter.split_text(text)


def process_document(file_path: str, chunk_size: int = 2050, chunk_overlap: int = 150) -> List[str]:
    """
    Process a document by loading it and splitting into chunks.
    
    Args:
        file_path: Path to the document file
        chunk_size: Maximum size of each chunk
        chunk_overlap: Overlap between consecutive chunks
        
    Returns:
        List of text chunks from the document
    """
    text = load_document(file_path)
    return split_text(text, chunk_size, chunk_overlap)