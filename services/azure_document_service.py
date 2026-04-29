import os
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from dotenv import load_dotenv

load_dotenv()

class AzureDocumentService:
    def __init__(self):
        endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
        
        if not endpoint or not key:
            raise ValueError("Missing Azure Document Intelligence credentials in .env")
            
        self.client = DocumentIntelligenceClient(
            endpoint=endpoint, credential=AzureKeyCredential(key)
        )

    def extract_invoice_data(self, file_bytes: bytes) -> dict:
        """
        Extracts invoice information using Azure Document Intelligence 'prebuilt-invoice' model.
        Returns a dictionary with raw extracted values.
        """
        # Analyze document
        poller = self.client.begin_analyze_document(
            "prebuilt-invoice", AnalyzeDocumentRequest(bytes_source=file_bytes)
        )
        result = poller.result()

        extracted_data = {
            "date": None,
            "total_price": None,
            "purchased_items": [],
            "tax_number": None,
            "raw_text": result.content
        }

        if result.documents:
            # We usually only have one document if it's a single invoice image
            doc = result.documents[0]
            fields = doc.fields if doc.fields else {}

            # Extract Date
            if "InvoiceDate" in fields:
                extracted_data["date"] = fields.get("InvoiceDate").get("valueDate")

            # Extract Total Price
            if "InvoiceTotal" in fields:
                # ValueCurrency usually contains amount and currency
                currency_val = fields.get("InvoiceTotal").get("valueCurrency")
                if currency_val and "amount" in currency_val:
                    extracted_data["total_price"] = float(currency_val["amount"])
                else:
                    # fallback to valueNumber if available
                    extracted_data["total_price"] = fields.get("InvoiceTotal").get("valueNumber")

            # Extract Tax Number (TaxId)
            if "TaxId" in fields:
                extracted_data["tax_number"] = fields.get("TaxId").get("valueString")

            # Extract Purchased Items
            if "Items" in fields:
                items = fields.get("Items").get("valueArray", [])
                for item in items:
                    item_fields = item.get("valueObject", {})
                    # Usually "Description" holds the item name
                    if "Description" in item_fields:
                        desc = item_fields.get("Description").get("valueString")
                        if desc:
                            extracted_data["purchased_items"].append(desc)

        return extracted_data
