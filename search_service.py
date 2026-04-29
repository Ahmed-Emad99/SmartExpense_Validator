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
    SearchIndex,
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
                SimpleField(name="source_file", type=SearchFieldDataType.String, filterable=True, facetable=True),
                SimpleField(name="chunk_index", type=SearchFieldDataType.Int32),
                SimpleField(name="created_at", type=SearchFieldDataType.String, filterable=True),
            ]
            
            index = SearchIndex(name=self.index_name, fields=fields)
            
            result = self.index_client.create_index(index)
            print(f"Index '{self.index_name}' created successfully")
            return True
            
        except Exception as e:
            print(f"Error creating index: {str(e)}")
            raise Exception(f"Failed to create index: {str(e)}")
    
    def index_documents(self, documents: List[Dict]) -> Dict:
        """
        Index documents in Azure AI Search
        
        Args:
            documents: List of documents to index
            
        Returns:
            Dict: Indexing result information
        """
        try:
            result = self.search_client.upload_documents(documents)
            
            successful = sum(1 for r in result if r.succeeded)
            failed = sum(1 for r in result if not r.succeeded)
            
            print(f"Indexed {successful} documents successfully, {failed} failed")
            
            return {
                "total_documents": len(documents),
                "successful": successful,
                "failed": failed,
                "status": "completed"
            }
        except Exception as e:
            raise Exception(f"Failed to index documents: {str(e)}")
    
    def delete_documents_by_source(self, source_file: str) -> Dict:
        """
        Delete all documents from a specific source file
        
        Args:
            source_file: Name of the source file
            
        Returns:
            Dict: Deletion result information
        """
        try:
            # Search for all documents from this source
            results = self.search_client.search(
                search_text="*",
                filter=f"source_file eq '{source_file}'",
                select=["id"]
            )
            
            doc_ids = [result["id"] for result in results]
            
            if not doc_ids:
                return {"deleted_count": 0, "status": "no_documents_found"}
            
            # Delete documents
            delete_docs = [{"id": doc_id} for doc_id in doc_ids]
            result = self.search_client.delete_documents(delete_docs)
            
            return {
                "deleted_count": len(doc_ids),
                "status": "completed"
            }
        except Exception as e:
            raise Exception(f"Failed to delete documents: {str(e)}")
    
    def keyword_search(self, query: str, top_k: int = 5, 
                      source_file: Optional[str] = None) -> List[Dict]:
        """
        Perform keyword search on documents
        
        Args:
            query: Search query
            top_k: Number of results to return
            source_file: Optional filter by source file
            
        Returns:
            List[Dict]: Search results
        """
        try:
            filters = None
            if source_file:
                filters = f"source_file eq '{source_file}'"
            
            results = self.search_client.search(
                search_text=query,
                filter=filters,
                top=top_k,
                select=["id", "content", "page_number", "source_file", "chunk_index"]
            )
            
            search_results = []
            for result in results:
                search_results.append({
                    "id": result["id"],
                    "content": result["content"],
                    "page_number": result.get("page_number", 0),
                    "source_file": result["source_file"],
                    "score": result["@search.score"],
                })
            
            return search_results
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
                facets=["source_file"],
                top=0
            )
            
            # Extract facets
            facets = results.get_facets() if hasattr(results, 'get_facets') else {}
            
            if "source_file" in facets:
                sources = [item["value"] for item in facets["source_file"]]
                return sources
            
            # Fallback: search for unique source_file values
            results = self.search_client.search(search_text="*", select=["source_file"], top=1000)
            sources = list(set([result["source_file"] for result in results]))
            return sources
            
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
            print(f"Index '{self.index_name}' deleted successfully")
            return True
        except Exception as e:
            print(f"Error deleting index: {str(e)}")
            return False
