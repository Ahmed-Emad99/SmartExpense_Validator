import time
from datetime import date
import streamlit as st
import os

from services.invoice.invoice_processor import InvoiceProcessor
from services.blob_storage_service import BlobStorageService
from services.invoice.validation_service import ValidationService
from services.config import AzureConfig
from services.policy_rag.rag_service import RAGService
from services.policy_rag.chat_service import ChatService
from services.policy_rag.search_service import AzureSearchService
from services.policy_rag.doc_processor import DocumentProcessor
from services.policy_rag.doc_intelligence_service import DocumentIntelligenceService
from policy_check import pipeline, policy_validation
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
    "chat_history": [],
    "indexed_documents": [],
    "current_document": None,
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

@st.cache_resource
def get_rag_services():
    try:
        config = AzureConfig()
        search_service = AzureSearchService(
            config.search_endpoint,
            config.search_key,
            config.search_index_name
        )
        search_service.create_index()
        rag_service = RAGService(search_service)
        chat_service = ChatService(
            rag_service,
            azure_endpoint=config.azure_openai_endpoint,
            azure_key=config.azure_openai_key,
            api_version=config.azure_openai_api_version,
            model=config.azure_openai_model
        )
        return {
            "config": config,
            "search_service": search_service,
            "rag_service": rag_service,
            "chat_service": chat_service,
        }
    except Exception as e:
        st.warning(f"RAG services unavailable: {e}")
        return None

@st.cache_resource
def get_policy_blob_service():
    try:
        from services.config import AzureConfig
        config = AzureConfig()
        from services.blob_storage_service import BlobStorageService
        blob_svc = BlobStorageService()
        blob_svc.container_name = "policies"  # Use policies container
        blob_svc._ensure_container()
        return blob_svc
    except Exception as e:
        st.warning(f"Policy storage unavailable: {e}")
        return None

@st.cache_resource
def get_policy_doc_service():
    try:
        from services.config import AzureConfig
        config = AzureConfig()
        from services.policy_rag.doc_intelligence_service import DocumentIntelligenceService
        return DocumentIntelligenceService(
            config.doc_intelligence_endpoint,
            config.doc_intelligence_key
        )
    except Exception as e:
        st.warning(f"Document Intelligence unavailable: {e}")
        return None

processor = get_processor()
blob_svc = get_blob_service()
rag_services = get_rag_services()
policy_blob_svc = get_policy_blob_service()
policy_doc_service = get_policy_doc_service()
policy_processor = DocumentProcessor(chunk_size=2000, chunk_overlap=300) if rag_services else None


# Function to run policy pipeline once
def run_policy_pipeline():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    policy_doc_path = os.path.join(current_dir, "docs", "Comprehensive Corporate Travel.pdf")
    
    
    if not os.path.exists(policy_doc_path):
        print("--> File is not exist")
        return None
    
    try:
        # Load PDF text
        text = pipeline.load_pdf(policy_doc_path)
        print (f"---> Loaded {len(text)} characters from policy document")
    
        # Chunk the text
        chunks = pipeline.chunk_text(text, chunk_size=500, overlap=100)
        print(f"--->Created {len(chunks)} chunks")

        # Embed chunks
        embedded_chunks = pipeline.embed_chunks(chunks)
        print(f"-->Embedded {len(embedded_chunks)} chunks")
    
        # Create index if needed
        pipeline.create_index()
        print("--> index created")
    
        # Store in Azure Search
        pipeline.store_chunks(embedded_chunks)
        
        print("---> ✅ Policy pipeline completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error running policy pipeline: {str(e)}")
        return None


# Function to validate invoice against policy
def validate_invoice_policy(invoice_data):
    """
    Validate an invoice against the policy using policy_validation module.
    Returns the invoice with updated is_valid and validation_message if policy is invalid.
    """
    try:
        # Run policy validation
        validated_invoice = policy_validation.validate_against_policy(invoice_data)
        return validated_invoice
    except Exception as e:
        print(f"⚠️ Policy validation error: {str(e)}")
        return invoice_data


# SIDEBAR — Policy Management & Chatbot
with st.sidebar:
    
    st.markdown("---")
    if "run_policy_pipeline" not in st.session_state:
        st.session_state.run_policy_pipeline = run_policy_pipeline()

    if rag_services and policy_blob_svc and policy_doc_service:
        # Policy document upload section
        st.subheader("📤 Upload Policy Document")
        st.caption("Upload your travel policy PDF for the chatbot to reference")
        
        policy_file = st.file_uploader("Choose a policy PDF", type="pdf", key="policy_upload")
        folder_name = st.text_input("Folder name (optional)", value="policies", key="policy_folder")
        
        if policy_file and st.button("Upload & Index Policy", use_container_width=True, key="upload_policy_btn"):
            
            try:
                # Stage 1: Upload to Blob Storage
                st.info("📤 Stage 1/5: Uploading PDF to Azure Blob Storage...")
                upload_info = policy_blob_svc.upload_pdf(policy_file, folder_name)
                st.success("✅ PDF uploaded")
                
                # Stage 2: Generate SAS URL
                st.info("🔐 Stage 2/5: Generating access URL...")
                sas_url = policy_blob_svc.get_blob_sas_url(upload_info["blob_name"])
                st.success("✅ Access URL generated")
                
                # Stage 3: Extract text with Document Intelligence
                st.info("📖 Stage 3/5: Extracting text from PDF (this may take 10-30 seconds)...")
                doc_result = policy_doc_service.analyze_document(sas_url)
                pages_data = policy_doc_service.extract_text_by_page(doc_result)
                total_chars = sum(len(p["text"]) for p in pages_data)
                st.success(f"✅ Text extracted ({total_chars:,} characters across {len(pages_data)} pages)")
                
                # Stage 4: Process into chunks
                st.info("✂️ Stage 4/5: Processing document into chunks...")
                st.write(f"📊 Document size: {total_chars:,} characters across {len(pages_data)} pages")
                
                chunk_start = time.time()
                all_chunks = []
                for page_info in pages_data:
                    page_chunks = policy_processor.chunk_text(
                        page_info["text"],
                        policy_file.name,
                        page_number=page_info["page_number"]
                    )
                    all_chunks.extend(page_chunks)
                
                chunk_time = time.time() - chunk_start
                st.write(f"✅ Created {len(all_chunks)} chunks in {chunk_time:.2f}s")
                st.success("✅ Chunking complete")
                
                # Stage 5: Index in Azure AI Search
                st.info(f"🔍 Stage 5/5: Indexing {len(all_chunks)} chunks in Azure AI Search...")
                documents = policy_processor.prepare_for_indexing(all_chunks)
                rag_services["search_service"].index_documents(documents)
                st.success(f"✅ Indexed {len(documents)} document chunks successfully!")
                
                # Update indexed documents
                st.session_state.indexed_documents = rag_services["search_service"].get_all_sources()
                st.session_state.current_document = policy_file.name
                st.rerun()
                    
            except Exception as e:
                st.error(f"❌ Error processing document: {str(e)}")
        
        st.markdown("---")
        
        # Show indexed documents
        st.subheader("📚 Indexed Documents")
        indexed = rag_services["search_service"].get_all_sources()
        st.session_state.indexed_documents = indexed
        
        if indexed:
            for doc in indexed:
                st.markdown(f"✅ {doc}")
        else:
            st.info("ℹ️ No policy documents indexed yet. Upload one above.")
        
        st.markdown("---")
        
        # Chat history section
        st.subheader("💬 Chat History")
        if st.session_state.chat_history:
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
            if st.button("🔄 Clear Chat", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()
        else:
            st.info("💭 Chat history appears here")
    else:
        st.error("❌ Policy services not available. Check your Azure configuration.")

# Policy Chat Input (outside sidebar)
if rag_services:
    st.markdown("---")
    st.subheader("💬 Ask About Travel Policy")
    
    # Check if documents are indexed
    indexed_docs = rag_services["search_service"].get_all_sources()
    
    if indexed_docs:
        # Use a form to capture input
        with st.form(key="policy_form"):
            policy_question = st.text_input("Ask a question about company travel policy:", key="policy_input")
            submitted = st.form_submit_button("Ask", type="primary")
        
        if submitted and policy_question:
            # Add user message
            st.session_state.chat_history.append({"role": "user", "content": policy_question})
            
            # Generate RAG response
            with st.spinner("🔍 Searching policy documents..."):
                try:
                    response = rag_services["chat_service"].chat_with_rag(
                        user_query=policy_question,
                        chat_history=st.session_state.chat_history[:-1],
                        top_k=5
                    )
                    assistant_reply = response["answer"]
                except Exception as e:
                    assistant_reply = f"⚠️ Error generating response: {str(e)}"

            st.session_state.chat_history.append({"role": "assistant", "content": assistant_reply})
            
            # Display response
            st.success("✅ Answer generated:")
            st.info(f"**Answer:** {assistant_reply}")
            
            if response.get("sources"):
                with st.expander("📚 View Source Documents"):
                    for i, source in enumerate(response["sources"], 1):
                        st.markdown(f"**Source {i}:** {source['source_file']} (Page {source['page_number']})")
                        st.markdown(f"*Relevance: {source['score']:.2f}*")
                        st.markdown(f"> {source['content'][:300]}...")
    else:
        st.warning("⚠️ No policy documents indexed yet. Please upload a policy PDF in the sidebar first.")



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

                # Layer 3: Policy validation (only if invoice is still valid from previous layers)
                if invoice_data.is_valid:
                    status_text.text(f"Validating {display_id} against policy...")
                    invoice_data = validate_invoice_policy(invoice_data)
                    if invoice_data.is_valid:
                        st.success(f"✅ {display_id} passed policy validation")
                    else:
                        st.error(f"❌ {display_id} failed policy validation")
                        # Show the policy violation details
                        with st.expander(f"View Policy Details: {display_id}"):
                            st.markdown(invoice_data.validation_message)

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
    
    # Policy Validation Results Section
    st.subheader("📋 Policy Validation Results")
    
    policy_valid_count = 0
    policy_invalid_count = 0
    policy_inconclusive_count = 0
    
    for inv_id, inv_data in st.session_state.invoices.items():
        display_id = f"Invoice {inv_id.split('_')[1]}"
        
        # Check if invoice has policy validation message (contains ❌ or ⚠️ or policy)
        if inv_data.validation_message and ("❌" in inv_data.validation_message or "policy" in inv_data.validation_message.lower() or "⚠️" in inv_data.validation_message):
            if "❌" in inv_data.validation_message:
                policy_invalid_count += 1
                with st.expander(f"❌ Policy Violation: {display_id}"):
                    st.markdown(f"**Invoice ID:** {display_id}")
                    st.markdown(f"**Vendor:** {inv_data.vendor_name or 'N/A'}")
                    st.markdown(f"**Amount:** {inv_data.total_price} {inv_data.currency or ''}")
                    st.markdown("---")
                    st.markdown(inv_data.validation_message)
            elif "⚠️" in inv_data.validation_message:
                policy_inconclusive_count += 1
                with st.expander(f"⚠️ Policy Inconclusive: {display_id}"):
                    st.markdown(inv_data.validation_message)
        elif inv_data.is_valid:
            policy_valid_count += 1
    
    # Display summary
    if policy_invalid_count > 0:
        st.error(f"❌ {policy_invalid_count} invoice(s) failed policy validation")
    if policy_inconclusive_count > 0:
        st.warning(f"⚠️ {policy_inconclusive_count} invoice(s) have inconclusive policy checks")
    if policy_valid_count > 0:
        st.success(f"✅ {policy_valid_count} invoice(s) passed policy validation")
    
    if policy_valid_count == 0 and policy_invalid_count == 0 and policy_inconclusive_count == 0:
        st.info("ℹ️ No policy validation results yet. Run the policy pipeline first.")
    
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