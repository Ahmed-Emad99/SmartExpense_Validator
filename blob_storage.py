"""
Azure Blob Storage Handler
Handles all operations related to Azure Blob Storage
"""

from azure.storage.blob import BlobServiceClient
from typing import Tuple


class BlobStorageManager:
    """Manages Azure Blob Storage operations"""
    
    def __init__(self, connection_string: str, container_name: str = "uploads"):
        """
        Initialize BlobStorageManager
        
        Args:
            connection_string: Azure Storage connection string
            container_name: Name of the container to use (default: 'uploads')
        """
        self.connection_string = connection_string
        self.container_name = container_name
        self.blob_service_client = BlobServiceClient.from_connection_string(
            connection_string
        )
    
    def create_container_if_not_exists(self) -> bool:
        """
        Create container if it doesn't exist
        
        Returns:
            bool: True if container was created, False if it already existed
        """
        container_client = self.blob_service_client.get_container_client(
            self.container_name
        )
        
        try:
            container_client.get_container_properties()
            return False  # Container already exists
        except:
            self.blob_service_client.create_container(self.container_name)
            return True  # Container was created
    
    def sanitize_folder_name(self, folder_name: str) -> str:
        """
        Sanitize folder name for Azure Blob Storage
        
        Args:
            folder_name: Original folder name
            
        Returns:
            str: Sanitized folder name
        """
        return folder_name.strip().replace(" ", "-").lower()
    
    def upload_pdf(self, folder_name: str, pdf_file) -> Tuple[bool, str, str]:
        """
        Upload PDF file to Azure Blob Storage in a folder
        
        Args:
            folder_name: Name of the folder to create/use
            pdf_file: PDF file object from Streamlit file uploader
            
        Returns:
            Tuple: (success: bool, folder_path: str, blob_name: str)
            
        Raises:
            Exception: If upload fails
        """
        # Sanitize folder name
        folder_path = self.sanitize_folder_name(folder_name)
        
        # Create blob name with folder structure
        blob_name = f"{folder_path}/{pdf_file.name}"
        
        # Get blob client
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name,
            blob=blob_name
        )
        
        # Upload the file
        blob_client.upload_blob(pdf_file.getvalue(), overwrite=True)
        
        return True, folder_path, blob_name
    
    def list_blobs_in_folder(self, folder_path: str) -> list:
        """
        List all blobs in a specific folder
        
        Args:
            folder_path: Folder path to list
            
        Returns:
            list: List of blob names in the folder
        """
        container_client = self.blob_service_client.get_container_client(
            self.container_name
        )
        
        blobs = []
        for blob in container_client.list_blobs(name_starts_with=folder_path):
            blobs.append(blob.name)
        
        return blobs
    
    def delete_blob(self, blob_name: str) -> bool:
        """
        Delete a blob from storage
        
        Args:
            blob_name: Name of the blob to delete
            
        Returns:
            bool: True if deleted successfully
        """
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name,
            blob=blob_name
        )
        
        blob_client.delete_blob()
        return True


def upload_pdf_to_blob(
    connection_string: str,
    folder_name: str,
    pdf_file,
    container_name: str = "uploads"
) -> Tuple[bool, dict]:
    """
    Standalone function to upload PDF to Azure Blob Storage
    
    Args:
        connection_string: Azure Storage connection string
        folder_name: Folder name to create/use
        pdf_file: PDF file object from Streamlit file uploader
        container_name: Container name (default: 'uploads')
        
    Returns:
        Tuple: (success: bool, result_dict: dict with details)
    """
    try:
        manager = BlobStorageManager(connection_string, container_name)
        
        # Create container if needed
        container_created = manager.create_container_if_not_exists()
        
        # Upload PDF
        success, folder_path, blob_name = manager.upload_pdf(folder_name, pdf_file)
        
        return True, {
            "success": success,
            "folder_path": folder_path,
            "blob_name": blob_name,
            "file_name": pdf_file.name,
            "container_name": container_name,
            "container_created": container_created
        }
    except Exception as e:
        return False, {
            "error": str(e)
        }
