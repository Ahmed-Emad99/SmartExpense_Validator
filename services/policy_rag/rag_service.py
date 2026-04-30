"""
RAG Service Module
Handles retrieval-augmented generation operations
"""

from typing import List, Dict, Optional, Tuple


class RAGService:
    """Service for RAG operations - retrieving relevant documents and preparing context"""
    
    def __init__(self, search_service):
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
        return """You are a helpful corporate travel policy assistant. 
You have access to the company's comprehensive travel policy documents.

When answering questions:
1. Reference the relevant policy sections from the retrieved documents
2. Be clear and concise
3. If information is not found in the documents, say so explicitly
4. Provide page references where applicable
5. Highlight any important restrictions or requirements"""
