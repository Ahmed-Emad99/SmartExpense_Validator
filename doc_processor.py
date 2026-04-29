"""
Document Processing Module
Handles document chunking and text preparation for indexing
"""

from typing import List, Dict
from datetime import datetime


class DocumentChunk:
    """Represents a chunk of a document"""
    
    def __init__(self, content: str, chunk_id: str, page_number: int, 
                 source_file: str, chunk_index: int):
        """
        Initialize a document chunk
        
        Args:
            content: Text content of the chunk
            chunk_id: Unique identifier for the chunk
            page_number: Page number in original document
            source_file: Name of the source file
            chunk_index: Index of this chunk in the document
        """
        self.content = content
        self.chunk_id = chunk_id
        self.page_number = page_number
        self.source_file = source_file
        self.chunk_index = chunk_index
        self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        """Convert chunk to dictionary"""
        return {
            "id": self.chunk_id,
            "content": self.content,
            "page_number": self.page_number,
            "source_file": self.source_file,
            "chunk_index": self.chunk_index,
            "created_at": self.created_at,
        }


class DocumentProcessor:
    """Service for processing and chunking documents"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize Document Processor
        
        Args:
            chunk_size: Size of each chunk in characters
            chunk_overlap: Overlap between chunks in characters
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_text(self, text: str, source_file: str, page_number: int = 1) -> List[DocumentChunk]:
        """
        Split text into overlapping chunks (optimized for speed)
        
        Args:
            text: Text to chunk
            source_file: Name of the source file
            page_number: Page number
            
        Returns:
            List[DocumentChunk]: List of document chunks
        """
        if not text or len(text.strip()) == 0:
            return []
        
        chunks = []
        chunk_index = 0
        start = 0
        text_len = len(text)
        max_iterations = text_len // (self.chunk_size - self.chunk_overlap) + 10  # Safety limit
        iterations = 0
        
        while start < text_len and iterations < max_iterations:
            iterations += 1
            end = min(start + self.chunk_size, text_len)
            
            # Ensure we always make progress
            if end == start:
                break
            
            chunk_text = text[start:end].strip()
            
            if chunk_text:  # Only create chunk if there's actual content
                # Sanitize filename for Azure AI Search (no spaces allowed in keys)
                sanitized_filename = source_file.replace('.pdf', '').replace(' ', '-').replace('_', '-')
                chunk_id = f"{sanitized_filename}-page{page_number}-chunk{chunk_index}"
                chunk = DocumentChunk(
                    content=chunk_text,
                    chunk_id=chunk_id,
                    page_number=page_number,
                    source_file=source_file,
                    chunk_index=chunk_index
                )
                chunks.append(chunk)
                chunk_index += 1
            
            # Move start position, accounting for overlap
            # Ensure we always move forward
            step = max(1, self.chunk_size - self.chunk_overlap)
            start = start + step
        
        return chunks
    
    def process_document_text(self, full_text: str, source_file: str, 
                             pages_info: List[Dict] = None) -> List[DocumentChunk]:
        """
        Process entire document text into chunks
        
        Args:
            full_text: Complete text extracted from document
            source_file: Name of the source file
            pages_info: Optional list of dicts with page information
            
        Returns:
            List[DocumentChunk]: List of all chunks from the document
        """
        all_chunks = []
        
        # If we have page information, process by pages
        if pages_info:
            for page_info in pages_info:
                page_text = page_info.get('text', '')
                page_number = page_info.get('page_number', 1)
                
                page_chunks = self.chunk_text(page_text, source_file, page_number)
                all_chunks.extend(page_chunks)
        else:
            # Process entire document as single section
            all_chunks = self.chunk_text(full_text, source_file, 1)
        
        return all_chunks
    
    def prepare_for_indexing(self, chunks: List[DocumentChunk], 
                            additional_metadata: Dict = None) -> List[Dict]:
        """
        Prepare chunks for indexing in Azure AI Search
        
        Args:
            chunks: List of document chunks
            additional_metadata: Additional metadata to include
            
        Returns:
            List[Dict]: Formatted documents ready for indexing
        """
        documents = []
        
        for chunk in chunks:
            doc = {
                "id": chunk.chunk_id,
                "content": chunk.content,
                "page_number": chunk.page_number,
                "source_file": chunk.source_file,
                "chunk_index": chunk.chunk_index,
                "created_at": chunk.created_at,
            }
            
            # Add additional metadata if provided
            if additional_metadata:
                doc.update(additional_metadata)
            
            documents.append(doc)
        
        return documents
