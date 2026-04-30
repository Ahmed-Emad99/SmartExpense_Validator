import os
from datetime import date
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()


class BlobStorageService:
    """
    Handles uploading invoice files to Azure Blob Storage.
    All valid invoices land in a container
    """

    def __init__(self):
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "Invoices")

        if not connection_string:
            raise ValueError(
                "Missing AZURE_STORAGE_CONNECTION_STRING in .env. "
                "Find it in Azure Portal → Storage Account → Security + networking → Access keys."
            )

        self.connection_string = connection_string  # Store for later use
        self.client = BlobServiceClient.from_connection_string(connection_string)
        self._ensure_container()


    def upload_invoice(self, file_bytes: bytes, invoice_id: str, original_filename: str, travel_start: date, travel_end: date,) -> str:
        """
        Uploads a single invoice file to Blob Storage.

        Blob path pattern:
            {travel_start}__{travel_end}/{invoice_id}__{original_filename}

        Returns the full blob URL on success, raises on failure.
        """
        folder = f"{travel_start}__{travel_end}"
        blob_name = f"{folder}/{invoice_id}__{original_filename}"

        blob_client = self.client.get_blob_client(
            container=self.container_name, blob=blob_name
        )

        blob_client.upload_blob(file_bytes, overwrite=True)
        return blob_client.url

    def upload_invoices_batch(self, files: list[dict],  # each dict: {invoice_id, file_bytes, original_filename}
        travel_start: date, travel_end: date) -> dict[str, str]:
        """
        Uploads multiple invoices.
        Returns a mapping of invoice_id → blob URL (or error message).
        """
        results: dict[str, str] = {}
        for f in files:
            try:
                url = self.upload_invoice(
                    file_bytes=f["file_bytes"],
                    invoice_id=f["invoice_id"],
                    original_filename=f["original_filename"],
                    travel_start=travel_start,
                    travel_end=travel_end,
                )
                results[f["invoice_id"]] = url
            except Exception as e:
                results[f["invoice_id"]] = f"UPLOAD_ERROR: {str(e)}"
        return results


    def _ensure_container(self):
        """Creates the container if it doesn't already exist."""
        try:
            self.client.create_container(self.container_name)
        except Exception:
            # Container already exists — safe to ignore
            pass
    
    def upload_pdf(self, pdf_file, folder_name: str = "documents") -> dict:
        """
        Upload PDF file to blob storage (for policy documents)
        
        Args:
            pdf_file: File object from streamlit file_uploader
            folder_name: Folder name in blob storage
            
        Returns:
            dict: Contains blob_name, blob_url, folder_path, and file_name
        """
        try:
            # Ensure container exists
            self._ensure_container()
            
            # Create folder path (blob path with folder prefix)
            folder_path = folder_name.strip().replace(" ", "-").lower()
            blob_name = f"{folder_path}/{pdf_file.name}"
            
            # Get blob client and upload
            blob_client = self.client.get_blob_client(
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
    
    def get_blob_sas_url(self, blob_name: str, expiry_hours: int = 1) -> str:
        """
        Get SAS URL of a blob (for public access without credentials)
        
        Args:
            blob_name: Name of the blob
            expiry_hours: Number of hours the SAS token is valid (default: 1 hour)
            
        Returns:
            str: SAS URL of the blob
        """
        from datetime import datetime, timedelta
        from azure.storage.blob import generate_blob_sas, BlobSasPermissions
        
        try:
            # Parse connection string to get account name and key
            # Format: DefaultEndpointsProtocol=https;AccountName=xyz;AccountKey=abc==;EndpointSuffix=core.windows.net
            account_name = None
            account_key = None
            
            for part in self.connection_string.split(";"):
                if "=" in part:
                    key, _, value = part.partition("=")
                    if key == "AccountName":
                        account_name = value
                    elif key == "AccountKey":
                        account_key = value
            
            if not account_name or not account_key:
                raise ValueError("Could not parse account name or key from connection string")
            
            # Generate SAS token
            sas_token = generate_blob_sas(
                account_name=account_name,
                container_name=self.container_name,
                blob_name=blob_name,
                account_key=account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(hours=expiry_hours)
            )
            
            blob_client = self.client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            return f"{blob_client.url}?{sas_token}"
        except Exception as e:
            raise Exception(f"Failed to generate SAS URL: {str(e)}")