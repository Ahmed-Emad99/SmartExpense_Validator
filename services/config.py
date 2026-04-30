"""
Configuration and Credentials Management Module
Handles all configuration and Azure credentials
"""

import os
from dotenv import load_dotenv


class AzureConfig:
    """Configuration class for Azure services"""
    
    def __init__(self):
        """Initialize configuration by loading environment variables"""
        load_dotenv()
        
        # Blob Storage
        self.storage_connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.blob_container_name = "invoices"
        
        # Document Intelligence
        self.doc_intelligence_endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        self.doc_intelligence_key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
        
        # Azure AI Search
        self.search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        self.search_key = os.getenv("AZURE_SEARCH_KEY")
        self.search_index_name = "travel-policy-index"
        
        # Azure OpenAI (GPT-4o)
        self.azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.azure_openai_key = os.getenv("AZURE_OPENAI_KEY")
        self.azure_openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
        self.azure_openai_model = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
        
        self._validate_config()
    
    def _validate_config(self):
        """Validate that all required configuration is present"""
        required_fields = {
            "storage_connection_string": self.storage_connection_string,
            "doc_intelligence_endpoint": self.doc_intelligence_endpoint,
            "doc_intelligence_key": self.doc_intelligence_key,
            "search_endpoint": self.search_endpoint,
            "search_key": self.search_key,
            "azure_openai_endpoint": self.azure_openai_endpoint,
            "azure_openai_key": self.azure_openai_key,
        }
        
        missing_fields = [key for key, value in required_fields.items() if not value]
        
        if missing_fields:
            print(f"Warning: Missing environment variables: {', '.join(missing_fields)}")
    
    def get_all_config(self) -> dict:
        """
        Get all configuration as dictionary
        
        Returns:
            dict: Configuration dictionary
        """
        return {
            "storage_connection_string": self.storage_connection_string,
            "blob_container_name": self.blob_container_name,
            "doc_intelligence_endpoint": self.doc_intelligence_endpoint,
            "doc_intelligence_key": self.doc_intelligence_key,
            "search_endpoint": self.search_endpoint,
            "search_key": self.search_key,
            "search_index_name": self.search_index_name,
            "azure_openai_endpoint": self.azure_openai_endpoint,
            "azure_openai_key": self.azure_openai_key,
            "azure_openai_api_version": self.azure_openai_api_version,
            "azure_openai_model": self.azure_openai_model,
        }
