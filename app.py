import time
from datetime import date
import streamlit as st

from services.invoice_processor import InvoiceProcessor
from services.blob_storage_service import BlobStorageService
from services.validation_service import ValidationService
from utils.helpers import display_invoice_card
from utils.date_helpers import build_travel_session, format_deadline_warning


# Page config
st.set_page_config(
    page_title="SmartExpense Validator",
    page_icon="🧾",
    layout="wide",
)


# Session state initialisation
defaults = {
    "step": "dates",
    "invoices": {},     
    "upload_count": 0,
    "pending_files": [],
    "pending_filenames": [],
    "travel_session": None,
    "blob_urls": {},      
    "dummy_chat_history": [],
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


# Cached service initialisation
@st.cache_resource
def get_processor():
    try:
        return InvoiceProcessor()
    except Exception as e:
        st.error(f"Failed to initialise invoice processor: {e}")
        return None

@st.cache_resource
def get_blob_service():
    try:
        return BlobStorageService()
    except Exception as e:
        st.warning(f"Blob storage unavailable — invoices will not be archived: {e}")
        return None

processor = get_processor()
blob_svc  = get_blob_service()


# SIDEBAR — Policy Chatbot (DUMMY — RAG integration)
with st.sidebar:
    st.header("💬 Policy Assistant")
    st.caption("Ask anything about the travel expense policy.")

    # Render existing dummy history
    chat_container = st.container(height=420)
    with chat_container:
        for msg in st.session_state.dummy_chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # Accept user input and reply with a static placeholder
    user_input = st.chat_input("Ask about the policy…")
    if user_input:
        # Save and display user message
        st.session_state.dummy_chat_history.append({"role": "user", "content": user_input})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(user_input)


        dummy_reply = (
            "🔧 The policy assistant is being set up. "
        )

        st.session_state.dummy_chat_history.append({"role": "assistant", "content": dummy_reply})
        with chat_container:
            with st.chat_message("assistant"):
                st.markdown(dummy_reply)



# Invoice submission flow
st.title("🧾 SmartExpense Validator")
st.markdown("Submit your travel receipts for automatic extraction and validation.")

# ── STEP 0: Travel dates ──────────────────────────────────────────────────────
if st.session_state.step == "dates":
    st.subheader("1. Enter Your Travel Dates")
    st.markdown(
        "Your receipts must be dated within your travel window. "
        "You have **30 days after your return date** to upload them."
    )

    col1, col2 = st.columns(2)
    with col1:
        travel_start = st.date_input("✈️ Departure date", value=None, min_value=date(2000, 1, 1))
    with col2:
        travel_end = st.date_input("🏠 Return date", value=None, min_value=date(2000, 1, 1))

    if st.button("Confirm Dates", type="primary"):
        if not travel_start or not travel_end:
            st.error("Please select both a departure and a return date.")
        else:
            session, error = build_travel_session(travel_start, travel_end)
            if error:
                st.error(error)
            else:
                st.session_state.travel_session = session
                st.session_state.step = "upload"
                st.rerun()


# Upload Invoices
elif st.session_state.step == "upload":
    ts = st.session_state.travel_session

    st.subheader("2. Upload Invoices")

    warning = format_deadline_warning(ts)
    if warning:
        st.warning(warning)
    else:
        st.info(
            f"📅 Travel: **{ts.travel_start}** → **{ts.travel_end}** · "
            f"Upload deadline: **{ts.upload_deadline}**"
        )

    uploaded_files = st.file_uploader(
        "Choose invoice images or PDFs",
        type=["png", "jpg", "jpeg", "pdf"],
        accept_multiple_files=True,
    )

    if st.button("Process Invoices", type="primary") and uploaded_files:
        st.session_state.pending_files    = [f.read() for f in uploaded_files]
        st.session_state.pending_filenames = [f.name for f in uploaded_files]
        st.session_state.step = "processing"
        st.rerun()

# Processing Invoices 
elif st.session_state.step == "processing":
    st.subheader("Processing Invoices…")

    ts             = st.session_state.travel_session
    pending_bytes  = st.session_state.pending_files
    pending_names  = st.session_state.pending_filenames
    total_files    = len(pending_bytes)

    progress_bar = st.progress(0)
    status_text  = st.empty()
    blob_batch   = []

    for idx, (file_bytes, filename) in enumerate(zip(pending_bytes, pending_names)):
        st.session_state.upload_count += 1
        invoice_id = f"inv_{st.session_state.upload_count}"
        display_id = f"Invoice {st.session_state.upload_count}"

        status_text.text(f"Processing {display_id} ({filename})…")

        if processor:
            try:
                # Layer 1: extraction + field completeness
                invoice_data = processor.process_invoice(file_bytes, invoice_id, display_id)

                # Layer 2: business rules
                invoice_data = ValidationService.apply_business_rules(
                    invoice=invoice_data,
                    display_id=display_id,
                    travel_start=ts.travel_start,
                    travel_end=ts.travel_end,
                    upload_deadline=ts.upload_deadline,
                    existing_invoices=list(st.session_state.invoices.values()),
                )

                st.session_state.invoices[invoice_id] = invoice_data

                # Only archive invoices that passed ALL validation layers
                if invoice_data.is_valid:
                    blob_batch.append({
                        "invoice_id": invoice_id,
                        "file_bytes": file_bytes,
                        "original_filename": filename,
                    })

            except Exception as e:
                st.error(f"Error processing {display_id}: {e}")

        progress_bar.progress((idx + 1) / total_files)
        time.sleep(0.4)

    # Bulk upload to Azure Blob
    if blob_svc and blob_batch:
        status_text.text("Archiving invoices to Azure Blob Storage…")
        urls = blob_svc.upload_invoices_batch(
            files=blob_batch,
            travel_start=ts.travel_start,
            travel_end=ts.travel_end,
        )
        st.session_state.blob_urls.update(urls)

    status_text.text("Done!")
    st.session_state.pending_files    = []
    st.session_state.pending_filenames = []
    st.session_state.step = "review"
    st.rerun()

# Review & Validation
elif st.session_state.step == "review":
    st.subheader("3. Review & Validation")

    ts = st.session_state.travel_session
    st.info(
        f"📅 Travel: **{ts.travel_start}** → **{ts.travel_end}** · "
        f"Upload deadline: **{ts.upload_deadline}**"
    )

    # Session currency banner
    all_invoices = list(st.session_state.invoices.values())
    session_currency = ValidationService.get_session_currency(all_invoices)
    if session_currency:
        if "⚠️" in session_currency:
            st.warning(f"💱 Currency mismatch detected across invoices: **{session_currency}**")
        else:
            st.success(f"💱 Session currency: **{session_currency}**")

    valid_count   = 0
    invalid_count = 0

    for inv_id, inv_data in st.session_state.invoices.items():
        display_id = f"Invoice {inv_id.split('_')[1]}"
        status     = "VALID" if inv_data.is_valid else "INVALID"

        display_invoice_card(
            invoice_id=inv_id,
            display_name=display_id,
            status=status,
            message=inv_data.validation_message,
            is_valid=inv_data.is_valid,
        )

        if inv_data.is_valid:
            valid_count += 1
        else:
            invalid_count += 1

            with st.expander(f"🔄 Upload replacement for {display_id}"):
                replacement_file = st.file_uploader(
                    f"Choose replacement for {display_id}",
                    type=["png", "jpg", "jpeg", "pdf"],
                    key=f"repl_{inv_id}",
                )
                if (
                    st.button(f"Process Replacement for {display_id}", key=f"btn_repl_{inv_id}")
                    and replacement_file
                ):
                    with st.spinner(f"Processing replacement for {display_id}…"):
                        try:
                            file_bytes = replacement_file.read()

                            new_inv = processor.process_invoice(file_bytes, inv_id, display_id)

                            others = [
                                v for k, v in st.session_state.invoices.items()
                                if k != inv_id
                            ]
                            new_inv = ValidationService.apply_business_rules(
                                invoice=new_inv,
                                display_id=display_id,
                                travel_start=ts.travel_start,
                                travel_end=ts.travel_end,
                                upload_deadline=ts.upload_deadline,
                                existing_invoices=others,
                            )

                            st.session_state.invoices[inv_id] = new_inv

                            # Only archive if replacement passed validation
                            if new_inv.is_valid and blob_svc:
                                url = blob_svc.upload_invoice(
                                    file_bytes=file_bytes,
                                    invoice_id=inv_id,
                                    original_filename=replacement_file.name,
                                    travel_start=ts.travel_start,
                                    travel_end=ts.travel_end,
                                )
                                st.session_state.blob_urls[inv_id] = url

                            st.rerun()
                        except Exception as e:
                            st.error(f"Error processing replacement: {e}")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if invalid_count == 0:
            st.success("✅ All invoices are valid!")
            if st.button("Finish & View Summary", type="primary"):
                st.session_state.step = "done"
                st.rerun()
        else:
            st.warning(f"{invalid_count} invalid invoice(s). Please upload replacements above.")

    with col2:
        if st.button("Done (skip remaining replacements)"):
            st.session_state.step = "done"
            st.rerun()

# Summary
elif st.session_state.step == "done":
    st.subheader("4. Final Summary")

    ts               = st.session_state.travel_session
    all_invoices     = list(st.session_state.invoices.values())
    total_invoices   = len(all_invoices)
    valid_invoices   = sum(1 for i in all_invoices if i.is_valid)
    invalid_invoices = total_invoices - valid_invoices
    session_currency = ValidationService.get_session_currency(all_invoices)

    # Top metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Uploaded", total_invoices)
    col2.metric("✅ Valid",        valid_invoices)
    col3.metric("❌ Invalid",      invalid_invoices)
    col4.metric("💱 Currency",     session_currency or "—")

    if valid_invoices == total_invoices and total_invoices > 0:
        st.success(f"🎉 All {total_invoices} invoice(s) submitted and archived successfully.")
    else:
        st.info(f"Session complete: {valid_invoices} valid, {invalid_invoices} invalid.")

    # ── Extracted data table ──────────────────────────────────────────
    st.markdown("### Extracted Data")

    data_list = []
    for inv_id, inv_data in st.session_state.invoices.items():
        blob_url = st.session_state.blob_urls.get(inv_id, "—")

        # Format total with currency if available
        if inv_data.total_price is not None:
            currency_label = f" {inv_data.currency}" if inv_data.currency else ""
            total_display  = f"{inv_data.total_price:.2f}{currency_label}"
        else:
            total_display = "N/A"

        data_list.append({
            "ID":          f"Invoice {inv_id.split('_')[1]}",
            "Status":      "✅ Valid" if inv_data.is_valid else "❌ Invalid",
            "Date":        inv_data.date or "N/A",
            "Vendor":      inv_data.vendor_name or "N/A",
            "Total":       total_display,
            "Currency":    inv_data.currency or "N/A",
            "Items":       ", ".join(inv_data.purchased_items) if inv_data.purchased_items else "N/A",
            "Tax Number":  inv_data.tax_number or "N/A",
            "Blob URL":    blob_url,
        })

    st.dataframe(data_list, width='stretch')

    if st.button("Start New Session"):
        st.session_state.clear()
        st.rerun()