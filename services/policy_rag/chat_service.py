"""
Chat Service Module
Handles chat interactions with RAG capabilities
"""

from typing import List, Dict, Optional
from openai import AzureOpenAI


class ChatService:
    """Service for managing chat interactions with RAG"""
    
    def __init__(self, rag_service, azure_endpoint: str, azure_key: str, 
                 api_version: str = "2024-12-01-preview", model: str = "gpt-4o"):
        """
        Initialize Chat Service with Azure OpenAI
        
        Args:
            rag_service: Instance of RAGService
            azure_endpoint: Azure OpenAI endpoint
            azure_key: Azure OpenAI API key
            api_version: Azure OpenAI API version
            model: LLM model to use (default: gpt-4o)
        """
        self.rag_service = rag_service
        self.model = model
        
        self.client = AzureOpenAI(
            api_key=azure_key,
            api_version=api_version,
            azure_endpoint=azure_endpoint
        )
    
    def chat_with_rag(self, user_query: str, chat_history: List[Dict] = None,
                     source_file: Optional[str] = None, top_k: int = 5) -> Dict:
        """
        Chat with RAG context using Azure OpenAI
        
        Args:
            user_query: User's question
            chat_history: Previous chat messages
            source_file: Optional filter by source document
            top_k: Number of context documents to retrieve
            
        Returns:
            Dict: Response with answer and source documents
        """
        try:
            # Initialize chat history if not provided
            if chat_history is None:
                chat_history = []
            
            # Retrieve relevant context
            search_results, context = self.rag_service.retrieve_context(
                query=user_query,
                top_k=top_k,
                source_file=source_file
            )
            
            # Prepare system prompt
            system_prompt = self.rag_service.prepare_system_prompt()
            
            # Prepare messages
            messages = [
                {
                    "role": "system",
                    "content": system_prompt + "\n\nContext from documents:\n" + context
                }
            ]
            
            # Add chat history
            messages.extend(chat_history)
            
            # Add current user message
            messages.append({
                "role": "user",
                "content": user_query
            })
            
            # Get response from Azure OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            answer = response.choices[0].message.content
            
            return {
                "answer": answer,
                "sources": search_results,
                "query": user_query
            }
        except Exception as e:
            raise Exception(f"Chat failed: {str(e)}")
