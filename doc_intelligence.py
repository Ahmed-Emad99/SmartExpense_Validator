"""
Azure Document Intelligence Service Module
Handles all document intelligence operations
"""

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential


class DocumentIntelligenceService:
    """Service for managing Azure Document Intelligence operations"""
    
    def __init__(self, endpoint: str, api_key: str):
        """
        Initialize Document Intelligence Service
        
        Args:
            endpoint: Document Intelligence endpoint URL
            api_key: Document Intelligence API key
        """
        self.endpoint = endpoint
        self.api_key = api_key
        self.client = DocumentIntelligenceClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(api_key)
        )
    
    def analyze_document(self, document_url: str):
        """
        Analyze a document using prebuilt-read model
        
        Args:
            document_url: URL of the document to analyze
            
        Returns:
            AnalyzeResult: Result object containing extracted information
        """
        try:
            poller = self.client.begin_analyze_document(
                "prebuilt-read",
                AnalyzeDocumentRequest(url_source=document_url)
            )
            result = poller.result()
            return result
        except Exception as e:
            raise Exception(f"Failed to analyze document: {str(e)}")
    
    def extract_text(self, result) -> str:
        """
        Extract full text content from analysis result
        
        Args:
            result: AnalyzeResult object from analyze_document
            
        Returns:
            str: Extracted text content
        """
        full_text = ""
        if result.pages:
            for page in result.pages:
                if page.lines:
                    for line in page.lines:
                        full_text += line.content + "\n"
        return full_text
    
    def get_page_count(self, result) -> int:
        """
        Get total number of pages
        
        Args:
            result: AnalyzeResult object from analyze_document
            
        Returns:
            int: Number of pages
        """
        return len(result.pages) if result.pages else 0
    
    def get_page_details(self, result, page_index: int) -> dict:
        """
        Get detailed information about a specific page
        
        Args:
            result: AnalyzeResult object from analyze_document
            page_index: Index of the page (0-based)
            
        Returns:
            dict: Page details including content, tables, and metadata
        """
        if not result.pages or page_index >= len(result.pages):
            raise ValueError(f"Page index {page_index} out of range")
        
        page = result.pages[page_index]
        
        return {
            "page_number": page.page_number,
            "height": page.height,
            "width": page.width,
            "lines_count": len(page.lines) if page.lines else 0,
            "lines": [line.content for line in page.lines] if page.lines else [],
            "tables_count": len(page.tables) if page.tables else 0,
            "tables": [
                {
                    "row_count": table.row_count,
                    "column_count": table.column_count
                }
                for table in page.tables
            ] if page.tables else []
        }
    
    def get_all_pages_details(self, result) -> list:
        """
        Get detailed information about all pages
        
        Args:
            result: AnalyzeResult object from analyze_document
            
        Returns:
            list: List of page details for all pages
        """
        pages_details = []
        for idx in range(self.get_page_count(result)):
            pages_details.append(self.get_page_details(result, idx))
        return pages_details
