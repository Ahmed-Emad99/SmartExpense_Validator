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
        poller = self.client.begin_analyze_document(
            "prebuilt-invoice", AnalyzeDocumentRequest(bytes_source=file_bytes)
        )
        result = poller.result()

        extracted_data = {
            "date": None,
            "total_price": None,
            "currency": None,
            "purchased_items": [],
            "vendor_name": None,
            "tax_number": None,
            "raw_text": result.content,
        }

        if result.documents:
            doc = result.documents[0]
            fields = doc.fields if doc.fields else {}

            # Extract Date
            if "InvoiceDate" in fields:
                extracted_data["date"] = fields.get("InvoiceDate").get("valueDate")

            # Extract Total Price + Currency
            if "InvoiceTotal" in fields:
                currency_val = fields.get("InvoiceTotal").get("valueCurrency")
                if currency_val:
                    if "amount" in currency_val:
                        extracted_data["total_price"] = float(currency_val["amount"])
                    # currencyCode is the ISO code e.g. "USD", "EUR"
                    if "currencyCode" in currency_val:
                        extracted_data["currency"] = currency_val["currencyCode"]
                else:
                    extracted_data["total_price"] = fields.get("InvoiceTotal").get("valueNumber")

            # Extract Vendor Name
            if "VendorName" in fields:
                extracted_data["vendor_name"] = fields.get("VendorName").get("valueString")

            # Extract Tax Number
            if "TaxId" in fields:
                extracted_data["tax_number"] = fields.get("TaxId").get("valueString")

            # Extract Purchased Items
            if "Items" in fields:
                items = fields.get("Items").get("valueArray", [])
                for item in items:
                    item_fields = item.get("valueObject", {})
                    if "Description" in item_fields:
                        desc = item_fields.get("Description").get("valueString")
                        if desc:
                            extracted_data["purchased_items"].append(desc)

        return extracted_data