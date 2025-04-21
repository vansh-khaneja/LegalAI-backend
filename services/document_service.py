"""
Document processing service for the Legal AI application.

This module handles document loading, parsing, and text extraction
from various file formats.
"""

import os
import io
import logging
from typing import List, Optional, Dict, Any, BinaryIO, Tuple, Union

from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import docx
from docx import Document
from PyPDF2 import PdfReader

# Configure logging
logger = logging.getLogger(__name__)


class DocumentProcessingError(Exception):
    """Custom exception for document processing errors."""
    pass


def load_document_from_stream(file_stream: BinaryIO, file_name: str) -> str:
    """
    Load a document from a file stream and extract its text content.
    
    Args:
        file_stream: File-like object containing the document
        file_name: Name of the file (used to determine file type)
        
    Returns:
        Extracted text content from the document
        
    Raises:
        DocumentProcessingError: If document loading or text extraction fails
    """
    try:
        file_ext = os.path.splitext(file_name)[1].lower()
        
        if file_ext == ".pdf":
            return _load_pdf_from_stream(file_stream)
        elif file_ext == ".docx":
            return _load_docx_from_stream(file_stream)
        else:
            raise DocumentProcessingError(f"Unsupported file type: {file_ext}. Only PDF and DOCX are supported.")
    
    except Exception as e:
        logger.error(f"Error loading document '{file_name}': {e}")
        raise DocumentProcessingError(f"Failed to load document: {e}")


def _load_pdf_from_stream(file_stream: BinaryIO) -> str:
    """
    Load and extract text from a PDF file stream.
    
    Args:
        file_stream: File stream containing the PDF
        
    Returns:
        Extracted text content from the PDF
    """
    # Use PyPDF2 to extract text directly from the stream
    pdf_reader = PdfReader(file_stream)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text


def _load_docx_from_stream(file_stream: BinaryIO) -> str:
    """
    Load and extract text from a DOCX file stream.
    
    Args:
        file_stream: File stream containing the DOCX
        
    Returns:
        Extracted text content from the DOCX
    """
    doc = Document(file_stream)
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


def process_document_from_stream(file_stream: BinaryIO, file_name: str, 
                               chunk_size: int = 2050, chunk_overlap: int = 150) -> List[str]:
    """
    Process a document by loading it from a stream and splitting into chunks.
    
    Args:
        file_stream: File stream containing the document
        file_name: Name of the file (used to determine file type)
        chunk_size: Maximum size of each chunk
        chunk_overlap: Overlap between consecutive chunks
        
    Returns:
        List of text chunks from the document
    """
    text = load_document_from_stream(file_stream, file_name)
    return split_text(text, chunk_size, chunk_overlap)