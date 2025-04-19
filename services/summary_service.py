"""
LLM service for the Legal AI application.

This module handles interactions with language models for query routing,
question answering, and other NLP tasks.
"""

from langchain.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from langchain import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains.summarize import load_summarize_chain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from PyPDF2 import PdfReader
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
    
    def generate_summary(self, file_path:str) -> str:
        """
        Genrates the summary ot the file.
        
        Args:
            llm: Language Model instance
            file_path: Path to the document file
            
        Returns:
            Summary of the file
            
        Raises:
            SummarizationError: If summary generation fails
        """
        try:
            pdfreader = PdfReader(file_path)
            # read text from pdf
            text = ''
            for i, page in enumerate(pdfreader.pages):
                content = page.extract_text()
                if content:
                    text += content
            
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=20)
            chunks = text_splitter.create_documents([text])

            chain = load_summarize_chain(
                self.llm,
                chain_type='map_reduce',
                verbose=True
            )
            summary = chain.run(chunks)

            return summary
        except Exception as e:
            logger.error(f"Error Summarizing file: {e}")
            raise SummarizationError(f"Failed to route query: {e}")
    
 