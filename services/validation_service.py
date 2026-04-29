from models.invoice_model import InvoiceData

class ValidationService:
    @staticmethod
    def validate_invoice(invoice: InvoiceData, display_id: str) -> InvoiceData:
        """
        Validates an invoice based on required fields:
        - date
        - total_price
        - purchased_items (at least one)
        """
        missing_fields = []
        
        if not invoice.date:
            missing_fields.append("date")
            
        if invoice.total_price is None:
            missing_fields.append("total price")
            
        if not invoice.purchased_items or len(invoice.purchased_items) == 0:
            missing_fields.append("purchased item")
            
        if not missing_fields:
            invoice.is_valid = True
            invoice.validation_message = f"{display_id} is valid."
        else:
            invoice.is_valid = False
            if len(missing_fields) == 1:
                invoice.validation_message = f"{display_id} does not contain {missing_fields[0]}."
            elif len(missing_fields) > 1:
                fields_str = ", ".join(missing_fields[:-1]) + f" and {missing_fields[-1]}"
                invoice.validation_message = f"{display_id} does not contain {fields_str}."
                
        # Handle unclear case if it's completely empty
        if not invoice.date and invoice.total_price is None and not invoice.purchased_items:
            invoice.validation_message = f"{display_id} is unclear."

        return invoice
