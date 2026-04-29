"""
Azure Blob Storage Service Module
Handles all blob storage operations
"""

from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta


class BlobStorageService:
    """Service for managing Azure Blob Storage operations"""
    
    def __init__(self, connection_string: str):
        """
        Initialize Blob Storage Service
        
        Args:
            connection_string: Azure Storage connection string
        """
        self.connection_string = connection_string
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.container_name = "uploads"
    
    def ensure_container_exists(self) -> bool:
        """
        Check if container exists, create if it doesn't
        
        Returns:
            bool: True if container exists or was created, False otherwise
        """
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            container_client.get_container_properties()
            return True
        except:
            try:
                self.blob_service_client.create_container(self.container_name)
                return True
            except Exception as e:
                raise Exception(f"Failed to create container: {str(e)}")
    
    def upload_pdf(self, pdf_file, folder_name: str) -> dict:
        """
        Upload PDF file to blob storage
        
        Args:
            pdf_file: File object from streamlit file_uploader
            folder_name: Folder name in blob storage
            
        Returns:
            dict: Contains blob_name, blob_url, folder_path, and file_name
        """
        try:
            # Ensure container exists
            self.ensure_container_exists()
            
            # Create folder path (blob path with folder prefix)
            folder_path = folder_name.strip().replace(" ", "-").lower()
            blob_name = f"{folder_path}/{pdf_file.name}"
            
            # Get blob client and upload
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            blob_client.upload_blob(pdf_file.getvalue(), overwrite=True)
            
            return {
                "blob_name": blob_name,
                "blob_url": blob_client.url,
                "folder_path": folder_path,
                "file_name": pdf_file.name,
                "container_name": self.container_name
            }
        except Exception as e:
            raise Exception(f"Failed to upload PDF: {str(e)}")
    
    def get_blob_url(self, blob_name: str) -> str:
        """
        Get URL of a blob
        
        Args:
            blob_name: Name of the blob
            
        Returns:
            str: URL of the blob
        """
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name,
            blob=blob_name
        )
        return blob_client.url
    
    def get_blob_sas_url(self, blob_name: str, expiry_hours: int = 1) -> str:
        """
        Get SAS URL of a blob (for public access without credentials)
        
        Args:
            blob_name: Name of the blob
            expiry_hours: Number of hours the SAS token is valid (default: 1 hour)
            
        Returns:
            str: SAS URL of the blob
        """
        try:
            # Extract account name and key from connection string
            connection_dict = {}
            for part in self.connection_string.split(";"):
                if "=" in part:
                    key, value = part.split("=", 1)
                    connection_dict[key] = value
            
            account_name = connection_dict.get("AccountName")
            account_key = connection_dict.get("AccountKey")
            
            if not account_name or not account_key:
                raise Exception("Could not extract account name or key from connection string")
            
            # Generate SAS token
            sas_token = generate_blob_sas(
                account_name=account_name,
                container_name=self.container_name,
                blob_name=blob_name,
                account_key=account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(hours=expiry_hours)
            )
            
            # Construct SAS URL
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            sas_url = f"{blob_client.url}?{sas_token}"
            
            return sas_url
        except Exception as e:
            raise Exception(f"Failed to generate SAS URL: {str(e)}")
