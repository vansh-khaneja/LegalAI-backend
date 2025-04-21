"""
LLM service for the Legal AI application.

This module handles interactions with language models for query routing,
question answering, and other NLP tasks.
"""

import logging
from typing import Dict, Any, List, Optional, Literal

from groq import Groq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_groq import ChatGroq

# Configure logging
logger = logging.getLogger(__name__)


class LLMServiceError(Exception):
    """Custom exception for LLM service errors."""
    pass


class RouteQuery(BaseModel):
    """Routes a user query to the most relevant data source."""

    datasource: Literal["general", "casebased"] = Field(
        ...,
        description="Given a user question, choose to route it to either 'general' or 'casebased' data source.",
    )


class LLMService:
    """Service for handling language model operations."""
    
    def __init__(self, groq_api_key: str, model_name: str = "meta-llama/llama-4-scout-17b-16e-instruct"):
        """
        Initialize the LLM service.
        
        Args:
            groq_api_key: API key for Groq
            model_name: Name of the model to use
        """
        try:
            self.groq_client = Groq(api_key=groq_api_key)
            self.model_name = model_name
            
            # Initialize LangChain components
            self.llm = ChatGroq(
                groq_api_key=groq_api_key,
                model_name=model_name
            )
            self.structured_llm_router = self.llm.with_structured_output(RouteQuery)
            
            # Create router prompt
            self.route_prompt = ChatPromptTemplate.from_template("""
            Eres un enrutador de chatbot legal responsable de analizar las consultas de los usuarios y determinar si están relacionadas con temas legales o si son conversaciones generales.

            ## Instrucciones
            - Analiza la consulta del usuario para determinar si está relacionada con asuntos legales o si es un saludo/conversación general/pregunta fuera de tema.
            - Enruta la consulta a la fuente de datos "casebased" si contiene preguntas sobre leyes, consecuencias legales, procedimientos legales, derechos legales, documentos legales, casos judiciales, regulaciones, estatutos u otro tema legal.
            - Enruta a "general" si la consulta es un saludo (como "hola", "buenos días", "qué tal"), una charla trivial o claramente no relacionada con asuntos legales.
            - En caso de duda, favorece el enrutamiento a "casebased" para cualquier cosa que pueda tener implicaciones legales.

            ## Ejemplos
            - "¿Cuáles son las consecuencias del robo?" -> casebased
            - "Hola" -> general
            - "¿Cómo estás hoy?" -> general
            - "¿Cuál es la pena por infringir derechos de autor?" -> casebased
            - "¿Puedes explicar qué es el habeas corpus?" -> casebased
            - "Hoy me siento aburrido" -> general
            - "¿Cuál es la diferencia entre un delito grave y uno menor?" -> casebased

            Consulta del usuario: {question}
            """)
            
            # Create the question router
            self.question_router = self.route_prompt | self.structured_llm_router
            
            logger.info("LLM service initialized")
            
        except Exception as e:
            logger.error(f"Error initializing LLM service: {e}")
            raise LLMServiceError(f"Failed to initialize LLM service: {e}")
    
    def route_query(self, query: str) -> str:
        """
        Route a user query to the appropriate data source.
        
        Args:
            query: User query text
            
        Returns:
            Data source to use ("general" or "casebased")
            
        Raises:
            LLMServiceError: If query routing fails
        """
        try:
            route_result = self.question_router.invoke({"question": query})
            return route_result.datasource
        except Exception as e:
            logger.error(f"Error routing query: {e}")
            raise LLMServiceError(f"Failed to route query: {e}")
    
    def general_response(self, query: str) -> str:
        """
        Generate a response for a general query.
        
        Args:
            query: User query text
            
        Returns:
            Generated response text
            
        Raises:
            LLMServiceError: If response generation fails
        """
        try:
            chat_completion = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": f"""Esta es la pregunta: {query}. Actúa como si fueras un chatbot legal para asistir, así que responde en consecuencia.
                        
                    Tu respuesta debe ser completa pero concisa.""",
                    }
                ],
                model=self.model_name,
            )
            
            return chat_completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating general response: {e}")
            raise LLMServiceError(f"Failed to generate general response: {e}")
    
    def case_based_response(self, query: str, context: str) -> str:
        """
        Generate a response for a case-based query using the provided context.
        
        Args:
            query: User query text
            context: Context information from vector search
            
        Returns:
            Generated response text
            
        Raises:
            LLMServiceError: If response generation fails
        """
        try:
            chat_completion = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": f"""Esta es la pregunta: {query} y este es el contexto: {context}.
                            
            Proporciona una respuesta legal completa basada en el contexto proporcionado. Actúa como un asistente legal profesional para abogados. Tu respuesta debe:

            1. Incluir una respuesta clara y específica a la pregunta basada únicamente en el contexto dado  
            2. Formatear los puntos clave con espaciado y estructura adecuados  
            3. Usar **negrita** para principios legales importantes, referencias a casos o advertencias críticas  
            4. Usar saltos de párrafo con \\n\\n entre secciones distintas  
            5. Incluir viñetas donde sea apropiado para listar requisitos, factores o consideraciones  
            6. Si se citan regulaciones o estatutos específicos, formatearlos correctamente  
            7. Evitar jerga innecesaria y mantener la respuesta directa

            Tu respuesta debe ser completa pero concisa, enfocándose en la información legalmente relevante.""",
                    }
                ],
                model=self.model_name,
            )
            
            return chat_completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating case-based response: {e}")
            raise LLMServiceError(f"Failed to generate case-based response: {e}")