"""
Azure AI Search Service Module
Handles indexing and searching documents in Azure AI Search
"""

from typing import List, Dict, Optional
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
)
from azure.core.credentials import AzureKeyCredential


class AzureSearchService:
    """Service for managing Azure AI Search operations"""
    
    def __init__(self, endpoint: str, api_key: str, index_name: str):
        """
        Initialize Azure AI Search Service
        
        Args:
            endpoint: Azure AI Search endpoint URL
            api_key: Azure AI Search API key
            index_name: Name of the search index
        """
        self.endpoint = endpoint
        self.api_key = api_key
        self.index_name = index_name
        
        self.credential = AzureKeyCredential(api_key)
        self.index_client = SearchIndexClient(endpoint=endpoint, credential=self.credential)
        self.search_client = SearchClient(endpoint=endpoint, index_name=index_name, credential=self.credential)
    
    def create_index(self) -> bool:
        """
        Create search index schema
        
        Returns:
            bool: True if successful
        """
        try:
            # Check if index exists
            try:
                self.index_client.get_index(self.index_name)
                print(f"Index '{self.index_name}' already exists")
                return True
            except:
                pass  # Index doesn't exist, create it
            
            # Define index schema
            fields = [
                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="en.microsoft"),
                SimpleField(name="page_number", type=SearchFieldDataType.Int32),
                SimpleField(name="source_file", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="chunk_index", type=SearchFieldDataType.Int32),
                SimpleField(name="created_at", type=SearchFieldDataType.String),
            ]
            
            index = SearchIndex(
                name=self.index_name,
                fields=fields,
            )
            
            result = self.index_client.create_index(index)
            print(f"Created index '{self.index_name}'")
            return True
        except Exception as e:
            print(f"Error creating index: {str(e)}")
            return False
    
    def index_documents(self, documents: List[Dict]) -> bool:
        """
        Index documents in Azure AI Search
        
        Args:
            documents: List of documents to index
            
        Returns:
            bool: True if successful
        """
        try:
            result = self.search_client.upload_documents(documents)
            print(f"Indexed {len(documents)} documents")
            return True
        except Exception as e:
            raise Exception(f"Failed to index documents: {str(e)}")
    
    def keyword_search(self, query: str, top_k: int = 5, 
                      source_file: Optional[str] = None) -> List[Dict]:
        """
        Perform keyword search on indexed documents
        
        Args:
            query: Search query
            top_k: Number of top results to return
            source_file: Optional filter by source file
            
        Returns:
            List[Dict]: Search results with scores
        """
        try:
            filter_query = None
            if source_file:
                filter_query = f"source_file eq '{source_file}'"
            
            results = self.search_client.search(
                search_text=query,
                filter=filter_query,
                top=top_k
            )
            
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": result["id"],
                    "content": result["content"],
                    "page_number": result["page_number"],
                    "source_file": result["source_file"],
                    "score": result["@search.score"],
                })
            
            return formatted_results
        except Exception as e:
            raise Exception(f"Search failed: {str(e)}")
    
    def get_all_sources(self) -> List[str]:
        """
        Get all unique source files in the index
        
        Returns:
            List[str]: List of source file names
        """
        try:
            results = self.search_client.search(
                search_text="*",
                select=["source_file"],
                top=1000
            )
            sources = list(set([result["source_file"] for result in results if "source_file" in result]))
            return sorted(sources)
        except Exception as e:
            print(f"Error getting sources: {str(e)}")
            return []
    
    def delete_index(self) -> bool:
        """
        Delete the search index
        
        Returns:
            bool: True if successful
        """
        try:
            self.index_client.delete_index(self.index_name)
            print(f"Deleted index '{self.index_name}'")
            return True
        except Exception as e:
            print(f"Error deleting index: {str(e)}")
            return False
