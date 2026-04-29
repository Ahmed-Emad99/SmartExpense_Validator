from models.invoice_model import InvoiceData
from services.azure_document_service import AzureDocumentService
from services.validation_service import ValidationService

class InvoiceProcessor:
    def __init__(self):
        self.doc_service = AzureDocumentService()
        self.val_service = ValidationService()

    def process_invoice(self, file_bytes: bytes, invoice_id: str, display_id: str) -> InvoiceData:
        """
        Processes a single invoice:
        1. Extracts data using Azure Document Intelligence.
        2. Maps data to the InvoiceData model.
        3. Validates the extracted data.
        """
        # 1. Extract data
        extracted_dict = self.doc_service.extract_invoice_data(file_bytes)
        
        # 2. Map to Model
        invoice = InvoiceData(
            invoice_id=invoice_id,
            date=extracted_dict.get("date"),
            total_price=extracted_dict.get("total_price"),
            purchased_items=extracted_dict.get("purchased_items", []),
            tax_number=extracted_dict.get("tax_number"),
            raw_text=extracted_dict.get("raw_text")
        )
        
        # 3. Validate
        invoice = self.val_service.validate_invoice(invoice, display_id)
        
        return invoice
