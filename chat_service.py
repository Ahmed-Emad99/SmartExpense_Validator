"""
Chat Service Module
Handles chat interactions with RAG capabilities
"""

from typing import List, Dict, Optional
from openai import AzureOpenAI
from rag_service import RAGService


class ChatService:
    """Service for managing chat interactions with RAG"""
    
    def __init__(self, rag_service: RAGService, azure_endpoint: str, azure_key: str, 
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
            
            # Prepare messages for the model
            system_prompt = self.rag_service.prepare_system_prompt()
            chat_prompt = self.rag_service.prepare_chat_prompt(user_query, context, chat_history)
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": chat_prompt}
            ]
            
            # Get response from Azure OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000,
                top_p=0.95
            )
            
            answer = response.choices[0].message.content
            
            return {
                "answer": answer,
                "sources": search_results,
                "context": context,
                "model": self.model,
                "tokens_used": {
                    "prompt": response.usage.prompt_tokens,
                    "completion": response.usage.completion_tokens,
                    "total": response.usage.total_tokens
                }
            }
        except Exception as e:
            raise Exception(f"Chat failed: {str(e)}")
    
    def stream_chat_with_rag(self, user_query: str, chat_history: List[Dict] = None,
                            source_file: Optional[str] = None, top_k: int = 5):
        """
        Stream chat response with RAG context using Azure OpenAI (yields tokens as they arrive)
        
        Args:
            user_query: User's question
            chat_history: Previous chat messages
            source_file: Optional filter by source document
            top_k: Number of context documents to retrieve
            
        Yields:
            str: Streamed response tokens
        """
        try:
            if chat_history is None:
                chat_history = []
            
            # Retrieve relevant context
            search_results, context = self.rag_service.retrieve_context(
                query=user_query,
                top_k=top_k,
                source_file=source_file
            )
            
            # Prepare messages
            system_prompt = self.rag_service.prepare_system_prompt()
            chat_prompt = self.rag_service.prepare_chat_prompt(user_query, context, chat_history)
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": chat_prompt}
            ]
            
            # Stream response from Azure OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000,
                top_p=0.95,
                stream=True
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                        
        except Exception as e:
            yield f"Error during chat: {str(e)}"
    
    def format_sources_for_display(self, search_results: List[Dict]) -> str:
        """
        Format search results for display in UI
        
        Args:
            search_results: List of search results
            
        Returns:
            str: Formatted sources string
        """
        if not search_results:
            return "No sources used."
        
        sources_parts = []
        sources_parts.append("📚 **Sources Used:**")
        
        for i, result in enumerate(search_results, 1):
            sources_parts.append(
                f"{i}. {result['source_file']} (Page {result['page_number']}) - Score: {result['score']:.2f}"
            )
        
        return "\n".join(sources_parts)
    
    def get_available_documents(self) -> List[str]:
        """
        Get list of available documents for filtering
        
        Returns:
            List[str]: List of source documents
        """
        return self.rag_service.get_source_list()
