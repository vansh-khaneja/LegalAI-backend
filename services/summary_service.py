""" Summarization service for the Legal AI application.  This module handles document summarization using language models. """
from langchain_community.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from typing import BinaryIO

from langchain import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains.summarize import load_summarize_chain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from PyPDF2 import PdfReader
import docx  # Added for handling .docx files
import io
import logging

# Configure logging
logger = logging.getLogger(__name__)

class SummarizationError(Exception):
    """Custom exception for Summarization service errors."""
    pass

class SummarizationService:
    """Service for handling Summarization operations."""
    
    def __init__(self, groq_api_key: str, model_name: str = "llama3-8b-8192"):
        """
        Initialize the LLM service.
        
        Args:
            groq_api_key: API key for Groq
            model_name: Name of the model to use
        """
        try:
            self.model_name = model_name
            
            self.llm = ChatOpenAI(
                openai_api_key=groq_api_key,
                openai_api_base="https://api.groq.com/openai/v1",
                model=model_name,  # or "mixtral-8x7b-32768", etc.
            )
            
            logger.info("Summarizer service initialized")
            
        except Exception as e:
            logger.error(f"Error initializing LLM service: {e}")
            raise SummarizationError(f"Failed to initialize LLM service: {e}")
    
    def generate_summary_from_stream(self, file_stream: BinaryIO, file_name: str) -> str:
        """
        Generates the summary of the file from a stream.
        
        Args:
            file_stream: File stream containing the document
            file_name: Name of the file (used to determine file type)
            
        Returns:
            Summary of the file
            
        Raises:
            SummarizationError: If summary generation fails
        """
        try:
            # Reset the file stream position to the beginning
            file_stream.seek(0)
            
            if file_name.lower().endswith('.pdf'):
                # Use PdfReader for PDF files
                pdfreader = PdfReader(file_stream)
                
                # Read text from pdf
                text = ''
                for i, page in enumerate(pdfreader.pages):
                    content = page.extract_text()
                    if content:
                        text += content
            elif file_name.lower().endswith('.docx'):
                # Handle .docx files using python-docx library
                doc = docx.Document(file_stream)
                text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
            else:
                # For other file types, rely on the text that should have been extracted
                # by document_service already
                file_stream.seek(0)
                text = file_stream.read().decode('utf-8')
            
            # Split the text into manageable chunks
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=20)
            chunks = text_splitter.create_documents([text])
            
            # Use the summarization chain
            chain = load_summarize_chain(
                self.llm,
                chain_type='map_reduce',
                verbose=True
            )
            summary = chain.run(chunks)
            
            return summary
        except Exception as e:
            logger.error(f"Error summarizing file '{file_name}': {e}")
            raise SummarizationError(f"Failed to summarize file: {e}")