import streamlit as st
import time
from services.invoice_processor import InvoiceProcessor
from utils.helpers import display_invoice_card

# Configure page
st.set_page_config(page_title="SmartExpense Validator", page_icon="🧾", layout="wide")

# Initialize Session State
if "step" not in st.session_state:
    st.session_state.step = "upload"  # upload, processing, review, done
if "invoices" not in st.session_state:
    st.session_state.invoices = {}  # dict mapping invoice_id to InvoiceData
if "upload_count" not in st.session_state:
    st.session_state.upload_count = 0

# Initialize Services
@st.cache_resource
def get_processor():
    try:
        return InvoiceProcessor()
    except Exception as e:
        st.error(f"Failed to initialize Azure service: {str(e)}")
        return None

processor = get_processor()

# Main Title
st.title("🧾 SmartExpense Validator")
st.markdown("Upload your invoices for automatic data extraction and validation.")

# --- STEP 1: INITIAL UPLOAD ---
if st.session_state.step == "upload":
    st.subheader("1. Upload Invoices")
    uploaded_files = st.file_uploader(
        "Choose multiple invoice images or PDFs", 
        type=['png', 'jpg', 'jpeg', 'pdf'], 
        accept_multiple_files=True
    )
    
    if st.button("Process Invoices") and uploaded_files:
        st.session_state.step = "processing"
        # Temporarily store uploaded files in session to process them in the next rerun
        st.session_state.pending_files = uploaded_files
        st.rerun()

# --- STEP 2: PROCESSING ---
elif st.session_state.step == "processing":
    st.subheader("Processing Invoices...")
    pending_files = st.session_state.get("pending_files", [])
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_files = len(pending_files)
    
    for idx, file in enumerate(pending_files):
        # Generate Invoice ID
        st.session_state.upload_count += 1
        invoice_id = f"inv_{st.session_state.upload_count}"
        display_id = f"Invoice {st.session_state.upload_count}"
        
        status_text.text(f"Processing {display_id} ({file.name})...")
        
        if processor:
            try:
                # Read bytes
                file_bytes = file.read()
                # Process
                invoice_data = processor.process_invoice(file_bytes, invoice_id, display_id)
                # Save to state
                st.session_state.invoices[invoice_id] = invoice_data
            except Exception as e:
                st.error(f"Error processing {display_id}: {str(e)}")
        
        progress_bar.progress((idx + 1) / total_files)
        time.sleep(0.5) # Slight delay for UI feedback
        
    status_text.text("Processing complete!")
    st.session_state.pending_files = []
    st.session_state.step = "review"
    st.rerun()

# --- STEP 3: REVIEW & RE-UPLOAD ---
elif st.session_state.step == "review":
    st.subheader("2. Review & Validation")
    
    all_valid = True
    valid_count = 0
    invalid_count = 0
    
    # Display invoices
    for inv_id, inv_data in st.session_state.invoices.items():
        # Display ID
        display_id = f"Invoice {inv_id.split('_')[1]}"
        status = "VALID" if inv_data.is_valid else "INVALID"
        
        display_invoice_card(
            invoice_id=inv_id,
            display_name=display_id,
            status=status,
            message=inv_data.validation_message,
            is_valid=inv_data.is_valid
        )
        
        if inv_data.is_valid:
            valid_count += 1
        else:
            invalid_count += 1
            all_valid = False
            
            # Re-upload UI for invalid invoice
            with st.expander(f"Upload replacement for {display_id}"):
                replacement_file = st.file_uploader(
                    f"Choose replacement for {display_id}", 
                    type=['png', 'jpg', 'jpeg', 'pdf'], 
                    key=f"repl_{inv_id}"
                )
                if st.button(f"Process Replacement for {display_id}", key=f"btn_repl_{inv_id}") and replacement_file:
                    with st.spinner(f"Processing replacement for {display_id}..."):
                        try:
                            file_bytes = replacement_file.read()
                            new_inv_data = processor.process_invoice(file_bytes, inv_id, display_id)
                            st.session_state.invoices[inv_id] = new_inv_data
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error processing replacement: {str(e)}")

    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        if all_valid:
            st.success("All invoices are valid!")
            if st.button("Finish & View Summary", type="primary"):
                st.session_state.step = "done"
                st.rerun()
        else:
            st.warning(f"There are {invalid_count} invalid invoices. Please upload replacements.")
            
    with col2:
        if st.button("Done Uploading (Skip remaining replacements)"):
            st.session_state.step = "done"
            st.rerun()

# --- STEP 4: FINAL SUMMARY ---
elif st.session_state.step == "done":
    st.subheader("3. Final Summary")
    
    total_invoices = len(st.session_state.invoices)
    valid_invoices = sum(1 for inv in st.session_state.invoices.values() if inv.is_valid)
    invalid_invoices = total_invoices - valid_invoices
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Uploaded", total_invoices)
    col2.metric("Valid Invoices", valid_invoices)
    col3.metric("Invalid Invoices", invalid_invoices)
    
    if total_invoices > 0 and valid_invoices == total_invoices:
        st.success(f"🎉 {total_invoices} invoices uploaded successfully and registered.")
    else:
        st.info(f"Session finished with {valid_invoices} valid and {invalid_invoices} invalid invoices.")
        
    st.markdown("### Extracted Data Summary")
    
    # Create a simple table view of the data
    data_list = []
    for inv_id, inv_data in st.session_state.invoices.items():
        data_list.append({
            "ID": f"Invoice {inv_id.split('_')[1]}",
            "Status": "✅ Valid" if inv_data.is_valid else "❌ Invalid",
            "Date": inv_data.date if inv_data.date else "N/A",
            "Total Price": f"${inv_data.total_price}" if inv_data.total_price is not None else "N/A",
            "Items": ", ".join(inv_data.purchased_items) if inv_data.purchased_items else "N/A",
            "Tax Number": inv_data.tax_number if inv_data.tax_number else "N/A"
        })
        
    st.dataframe(data_list, use_container_width=True)
    
    if st.button("Start New Session"):
        st.session_state.clear()
        st.rerun()
