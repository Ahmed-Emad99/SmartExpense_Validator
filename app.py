import streamlit as st
import os
from dotenv import load_dotenv
from blob_storage import BlobStorageService
from doc_intelligence import DocumentIntelligenceService


# ============================================================================
# UI COMPONENTS AND FUNCTIONS
# ============================================================================

def setup_page():
    """Configure page settings"""
    st.set_page_config(page_title="PDF Upload to Azure Blob Storage", layout="centered")
    st.title("📄 PDF Upload to Azure Blob Storage")


def display_extracted_content(result):
    """
    Display extracted content in tabbed interface
    
    Args:
        result: AnalyzeResult object from Document Intelligence
    """
    doc_service = DocumentIntelligenceService("", "")
    
    st.success("✅ PDF processed successfully!")
    st.markdown("---")
    st.subheader("📖 Extracted Content")
    
    if result.pages:
        tab1, tab2 = st.tabs(["📄 Full Text", "📊 Details"])
        
        with tab1:
            full_text = doc_service.extract_text(result)
            if full_text:
                st.text_area(
                    "Full Text Content:",
                    value=full_text,
                    height=400,
                    disabled=False
                )
            else:
                st.info("No text content found in the PDF.")
        
        with tab2:
            pages_count = doc_service.get_page_count(result)
            st.write(f"**Total Pages:** {pages_count}")
            
            for idx, page in enumerate(result.pages, 1):
                with st.expander(f"Page {idx} Details"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Page Number:** {page.page_number}")
                        st.write(f"**Height:** {page.height}")
                    with col2:
                        st.write(f"**Width:** {page.width}")
                    
                    if page.lines:
                        st.write(f"**Number of Lines:** {len(page.lines)}")
                        st.markdown("**Extracted Lines:**")
                        lines_text = "\n".join([f"{i}. {line.content}" for i, line in enumerate(page.lines, 1)])
                        st.text(lines_text)
                    
                    # Check if tables attribute exists
                    if hasattr(page, 'tables') and page.tables:
                        st.write(f"**Number of Tables:** {len(page.tables)}")
                        for table_idx, table in enumerate(page.tables, 1):
                            st.write(f"**Table {table_idx}:**")
                            st.write(f"Rows: {table.row_count}, Columns: {table.column_count}")
    else:
        st.warning("⚠️ No pages found in the PDF.")


def display_upload_success(upload_info: dict):
    """
    Display upload success messages
    
    Args:
        upload_info: Dictionary containing upload information
    """
    st.success("✅ PDF uploaded successfully!")
    st.success(f"📁 Folder: {upload_info['folder_path']}")
    st.success(f"📄 File: {upload_info['file_name']}")
    st.info(f"📍 Blob path: {upload_info['blob_name']}")


def display_azure_configuration():
    """
    Display Azure configuration sidebar
    
    Returns:
        tuple: (connection_string, doc_intelligence_endpoint, doc_intelligence_key)
    """
    load_dotenv()
    
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    doc_intelligence_endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    doc_intelligence_key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
    
    st.sidebar.header("Azure Configuration")
    
    # Blob Storage Configuration
    if connection_string:
        st.sidebar.success("✅ Blob Storage connection string loaded")
    else:
        st.sidebar.warning("⚠️ Blob Storage connection string not found")
        connection_string = st.sidebar.text_input(
            "Azure Storage Connection String",
            type="password",
            help="Leave empty to use .env file, or enter connection string here"
        )
    
    st.sidebar.markdown("---")
    
    # Document Intelligence Configuration
    if doc_intelligence_endpoint and doc_intelligence_key:
        st.sidebar.success("✅ Document Intelligence credentials loaded")
    else:
        st.sidebar.warning("⚠️ Document Intelligence credentials not found")
        doc_intelligence_endpoint = st.sidebar.text_input(
            "Document Intelligence Endpoint",
            placeholder="https://<region>.api.cognitive.microsoft.com/",
            help="Leave empty to use .env file"
        )
        doc_intelligence_key = st.sidebar.text_input(
            "Document Intelligence Key",
            type="password",
            help="Leave empty to use .env file"
        )
    
    return connection_string, doc_intelligence_endpoint, doc_intelligence_key


def display_instructions():
    """Display application instructions and notes"""
    st.markdown("---")
    st.markdown("""
    ### 📋 Instructions:
    1. **Azure Blob Storage Setup**:
       - Go to Azure Portal → Storage Account → Access Keys → Copy Connection String
       - Store in `.env` file as `AZURE_STORAGE_CONNECTION_STRING`

    2. **Document Intelligence Setup**:
       - Create a Document Intelligence resource in Azure Portal
       - Copy the Endpoint and Key
       - Store in `.env` file as:
         - `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT`
         - `AZURE_DOCUMENT_INTELLIGENCE_KEY`

    3. **Upload and Process**:
       - Enter a folder name
       - Toggle "Single File" checkbox to switch between single and batch mode
       - Select your PDF file(s) - up to 5 files in batch mode
       - Click Upload PDF/PDFs

    ### 💡 Features:
    - 📤 Upload PDF to Azure Blob Storage
    - 📦 Batch upload support (up to 5 files)
    - 🔍 Process PDF with Azure Document Intelligence
    - 📖 Extract and display full text content
    - 📊 View detailed page information and tables

    ### 📝 Notes:
    - Folders are created as blob path prefixes
    - Document Intelligence extracts text, tables, and other content
    - Supports multi-page PDFs
    - Maximum 5 files per batch upload
    """)


def get_upload_inputs():
    """
    Get upload inputs from user with batch upload support
    
    Returns:
        tuple: (folder_name, pdf_files)
    """
    col1, col2 = st.columns(2)
    
    with col1:
        folder_name = st.text_input(
            "Enter Folder Name",
            placeholder="e.g., my-documents",
            help="The name of the folder to create in Azure Blob Storage"
        )
    
    with col2:
        st.write("")
        st.write("")
        single_mode = st.checkbox("Single File", value=True, help="Toggle to batch mode for multiple files")
    
    if single_mode:
        pdf_file = st.file_uploader(
            "Upload PDF File",
            type="pdf",
            help="Select a PDF file to upload"
        )
        pdf_files = [pdf_file] if pdf_file else []
    else:
        pdf_files = st.file_uploader(
            "Upload PDF Files (up to 5 files)",
            type="pdf",
            accept_multiple_files=True,
            help="Select multiple PDF files (maximum 5 files)"
        )
        if pdf_files and len(pdf_files) > 0:
            st.info(f"📁 {len(pdf_files)} file(s) selected")
    
    return folder_name, pdf_files


def render_upload_button(file_count=1):
    """
    Render upload button
    
    Args:
        file_count: Number of files to be uploaded
        
    Returns:
        bool: True if button is clicked
    """
    button_text = "📤 Upload PDFs" if file_count > 1 else "📤 Upload PDF"
    return st.button(button_text, use_container_width=True)


def show_validation_errors(connection_string, folder_name, pdf_files, doc_intelligence_endpoint, doc_intelligence_key):
    """
    Show validation errors
    
    Args:
        connection_string: Azure Storage connection string
        folder_name: Folder name input
        pdf_files: List of PDF files uploaded
        doc_intelligence_endpoint: Document Intelligence endpoint
        doc_intelligence_key: Document Intelligence API key
        
    Returns:
        bool: True if there are errors, False if validation passes
    """
    if not connection_string:
        st.error("❌ Please provide Azure Storage connection string")
        return True
    elif not folder_name:
        st.error("❌ Please enter a folder name")
        return True
    elif not pdf_files or len(pdf_files) == 0:
        st.error("❌ Please select at least one PDF file")
        return True
    elif len(pdf_files) > 5:
        st.error("❌ Maximum 5 files allowed per batch")
        return True
    elif not doc_intelligence_endpoint or not doc_intelligence_key:
        st.error("❌ Please provide Document Intelligence credentials")
        return True
    return False


def show_processing_spinner(message):
    """
    Show processing spinner
    
    Args:
        message: Spinner message
        
    Returns:
        Context manager for spinner
    """
    return st.spinner(message)


# ============================================================================
# MAIN APPLICATION
# ============================================================================

# Setup page
setup_page()

# Display Azure configuration sidebar
connection_string, doc_intelligence_endpoint, doc_intelligence_key = display_azure_configuration()

# Get upload inputs
folder_name, pdf_files = get_upload_inputs()

# Render upload button
if render_upload_button(len(pdf_files) if pdf_files else 1):
    # Validate inputs
    if show_validation_errors(connection_string, folder_name, pdf_files, doc_intelligence_endpoint, doc_intelligence_key):
        pass
    else:
        try:
            blob_service = BlobStorageService(connection_string)
            doc_service = DocumentIntelligenceService(
                doc_intelligence_endpoint,
                doc_intelligence_key
            )
            
            # Process each PDF file
            for idx, pdf_file in enumerate(pdf_files, 1):
                st.write(f"Processing file {idx}/{len(pdf_files)}: {pdf_file.name}")
                
                try:
                    # Upload to Blob Storage
                    with show_processing_spinner(f"⏳ Uploading {pdf_file.name}..."):
                        upload_info = blob_service.upload_pdf(pdf_file, folder_name)
                        display_upload_success(upload_info)
                    
                    # Process with Document Intelligence
                    with show_processing_spinner(f"⏳ Processing {pdf_file.name} with Document Intelligence..."):
                        sas_url = blob_service.get_blob_sas_url(upload_info["blob_name"])
                        result = doc_service.analyze_document(sas_url)
                        display_extracted_content(result)
                    
                    st.markdown("---")
                    
                except Exception as e:
                    st.error(f"❌ Error processing {pdf_file.name}: {str(e)}")
                    st.markdown("---")
                    
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.error(f"Details: {type(e).__name__}")

# Display instructions
display_instructions()