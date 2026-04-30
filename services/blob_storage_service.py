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