"""
RAG Service Module
Handles retrieval-augmented generation operations
"""

from typing import List, Dict, Optional, Tuple
from search_service import AzureSearchService


class RAGService:
    """Service for RAG operations - retrieving relevant documents and preparing context"""
    
    def __init__(self, search_service: AzureSearchService):
        """
        Initialize RAG Service
        
        Args:
            search_service: Instance of AzureSearchService
        """
        self.search_service = search_service
    
    def retrieve_context(self, query: str, top_k: int = 5, 
                        source_file: Optional[str] = None) -> Tuple[List[Dict], str]:
        """
        Retrieve relevant documents for a query using keyword search
        
        Args:
            query: User query
            top_k: Number of top results to retrieve
            source_file: Optional filter by source file
            
        Returns:
            Tuple[List[Dict], str]: List of relevant documents and formatted context string
        """
        try:
            # Perform keyword search
            search_results = self.search_service.keyword_search(
                query=query,
                top_k=top_k,
                source_file=source_file
            )
            
            # Format context from search results
            context = self._format_context(search_results)
            
            return search_results, context
        except Exception as e:
            raise Exception(f"Failed to retrieve context: {str(e)}")
    
    def _format_context(self, search_results: List[Dict]) -> str:
        """
        Format search results into a context string for the LLM
        
        Args:
            search_results: List of search results
            
        Returns:
            str: Formatted context string
        """
        if not search_results:
            return "No relevant documents found."
        
        context_parts = []
        context_parts.append(f"Found {len(search_results)} relevant documents:\n")
        
        for i, result in enumerate(search_results, 1):
            context_parts.append(f"\n--- Document {i} ---")
            context_parts.append(f"Source: {result['source_file']} (Page {result['page_number']})")
            context_parts.append(f"Relevance Score: {result['score']:.2f}")
            context_parts.append(f"Content:\n{result['content']}")
        
        return "\n".join(context_parts)
    
    def prepare_system_prompt(self) -> str:
        """
        Prepare system prompt for the chat model
        
        Returns:
            str: System prompt
        """
        return """You are a helpful assistant that answers questions based on the provided document context. 
Follow these guidelines:
1. Answer only based on the information provided in the document context
2. If the answer is not in the context, say "I couldn't find this information in the provided documents"
3. Be clear and concise in your responses
4. Cite which document or page the information comes from when relevant
5. If multiple sources have relevant information, mention all of them"""
    
    def prepare_chat_prompt(self, user_query: str, context: str, chat_history: List[Dict] = None) -> str:
        """
        Prepare the full chat prompt with context and history
        
        Args:
            user_query: Current user query
            context: Retrieved context from documents
            chat_history: Optional chat history
            
        Returns:
            str: Formatted prompt
        """
        prompt_parts = []
        
        # Add context
        prompt_parts.append("DOCUMENT CONTEXT:")
        prompt_parts.append("-" * 50)
        prompt_parts.append(context)
        prompt_parts.append("-" * 50)
        
        # Add chat history if available
        if chat_history and len(chat_history) > 0:
            prompt_parts.append("\nCONVERSATION HISTORY:")
            for message in chat_history[-5:]:  # Last 5 messages for context
                role = message.get("role", "").upper()
                content = message.get("content", "")
                prompt_parts.append(f"{role}: {content}")
        
        # Add current question
        prompt_parts.append(f"\nUSER QUESTION: {user_query}")
        
        return "\n".join(prompt_parts)
    
    def get_source_list(self) -> List[str]:
        """
        Get list of all indexed source documents
        
        Returns:
            List[str]: List of source files
        """
        return self.search_service.get_all_sources()
    
    def reindex_document(self, documents: List[Dict]) -> Dict:
        """
        Re-index documents (used for document updates)
        
        Args:
            documents: List of documents to index
            
        Returns:
            Dict: Indexing result
        """
        return self.search_service.index_documents(documents)
