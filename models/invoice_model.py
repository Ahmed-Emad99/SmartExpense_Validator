from pydantic import BaseModel
from typing import Optional, List

class InvoiceData(BaseModel):
    """
    Represents the extracted data from an invoice.
    """
    invoice_id: str
    date: Optional[str] = None
    total_price: Optional[float] = None
    currency: Optional[str] = None
    purchased_items: List[str] = []
    vendor_name: Optional[str] = None
    tax_number: Optional[str] = None
    raw_text: Optional[str] = None
    
    # Validation fields
    is_valid: bool = False
    validation_message: str = ""
