from datetime import date, datetime
from typing import List, Optional
from models.invoice_model import InvoiceData


class ValidationService:
    """
    Two-layer validation:

    Layer 1 — Field completeness (original logic, preserved exactly):
        • date present
        • total_price present
        • at least one purchased item

    Layer 2 — Business-rule checks:
        • Invoice date falls within the employee's travel window
        • Today's date is within the 30-day upload deadline
        • No duplicate detected (same date + same total + overlapping items + same vendor)
        • Currency is consistent across all invoices in the session
    """

    # Layer 1 — field completeness
    @staticmethod
    def validate_invoice(invoice: InvoiceData, display_id: str) -> InvoiceData:
        missing_fields = []

        if not invoice.date:
            missing_fields.append("date")

        if invoice.total_price is None:
            missing_fields.append("total price")

        if not invoice.purchased_items:
            missing_fields.append("purchased item")

        """if not invoice.tax_number:
            missing_fields.append("tax_number")"""

        if not invoice.vendor_name:
            missing_fields.append("vendor_name")

        if not missing_fields:
            invoice.is_valid = True
            invoice.validation_message = f"{display_id} is valid."
        else:
            invoice.is_valid = False
            if len(missing_fields) == 1:
                invoice.validation_message = (
                    f"{display_id} does not contain {missing_fields[0]}."
                )
            else:
                fields_str = ", ".join(missing_fields[:-1]) + f" and {missing_fields[-1]}"
                invoice.validation_message = (
                    f"{display_id} does not contain {fields_str}."
                )

        # Completely empty → unclear
        if not invoice.date and invoice.total_price is None and not invoice.purchased_items:
            invoice.validation_message = f"{display_id} is unclear."

        return invoice

    # Layer 2 — business rules
    @staticmethod
    def apply_business_rules(invoice: InvoiceData, display_id: str, travel_start: date, travel_end: date, upload_deadline: date, existing_invoices: Optional[List[InvoiceData]] = None,) -> InvoiceData:
        """
        Runs business-rule checks on an already field-validated invoice.
        Only runs when invoice.is_valid == True (won't overwrite a Layer-1 failure).
        Returns the (possibly updated) invoice.
        """
        if not invoice.is_valid:
            return invoice

        # 1. Upload deadline enforcement
        if date.today() > upload_deadline:
            invoice.is_valid = False
            invoice.validation_message = (
                f"{display_id} was uploaded after the submission deadline "
                f"({upload_deadline.strftime('%Y-%m-%d')}). "
                "Reimbursement window has closed."
            )
            return invoice

        # 2. Invoice date within travel window
        if invoice.date:
            try:
                inv_date = datetime.strptime(str(invoice.date), "%Y-%m-%d").date()
                if not (travel_start <= inv_date <= travel_end):
                    invoice.is_valid = False
                    invoice.validation_message = (
                        f"{display_id} date ({invoice.date}) is outside your travel "
                        f"window ({travel_start} → {travel_end})."
                    )
                    return invoice
            except ValueError:
                pass  # date format issue — skip range check, don't fail hard

        if existing_invoices:
            # 3. Currency consistency ------------------------------------
            #    Collect all currencies seen so far (ignore None values)
            session_currencies = {
                inv.currency
                for inv in existing_invoices
                if inv.currency is not None
            }
            if (
                invoice.currency is not None
                and session_currencies
                and invoice.currency not in session_currencies
            ):
                existing_currency = next(iter(session_currencies))
                invoice.is_valid = False
                invoice.validation_message = (
                    f"{display_id} has a different currency ({invoice.currency}) "
                    f"from the other invoices in this session ({existing_currency}). "
                    "All invoices must share the same currency."
                )
                return invoice

            # 4. Duplicate detection -------------------------------------
            #    Criteria: same date AND same total AND
            #              (same vendor if both have one) AND
            #              at least one overlapping purchased item
            for other in existing_invoices:
                if other.invoice_id == invoice.invoice_id:
                    continue

                same_date  = other.date == invoice.date
                same_total = other.total_price == invoice.total_price

                if not (same_date and same_total):
                    continue

                # Vendor check — only compare when both invoices have a vendor name
                vendor_match = True  # default: don't rule out on vendor alone
                if invoice.vendor_name and other.vendor_name:
                    vendor_match = (
                        invoice.vendor_name.strip().lower()
                        == other.vendor_name.strip().lower()
                    )

                # Item overlap check
                items_a = {i.strip().lower() for i in invoice.purchased_items}
                items_b = {i.strip().lower() for i in other.purchased_items}
                items_overlap = bool(items_a & items_b)

                if vendor_match and items_overlap:
                    invoice.is_valid = False
                    invoice.validation_message = (
                        f"{display_id} appears to be a duplicate of another invoice "
                        f"(same date, total, vendor, and overlapping items)."
                    )
                    return invoice

        return invoice

    
    # Currency summary helper
    @staticmethod
    def get_session_currency(invoices: List[InvoiceData]) -> Optional[str]:
        """
        Returns the single currency used across all invoices,
        or None if no currency info was extracted.
        """
        currencies = {inv.currency for inv in invoices if inv.currency}
        if len(currencies) == 1:
            return currencies.pop()
        if len(currencies) > 1:
            return "Mixed ⚠️"
        return None