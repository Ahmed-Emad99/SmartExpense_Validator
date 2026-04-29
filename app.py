import streamlit as st
import os
from dotenv import load_dotenv
from blob_storage import upload_pdf_to_blob

# Load environment variables from .env file
load_dotenv()

# Page configuration
st.set_page_config(page_title="PDF Upload to Azure Blob Storage", layout="centered")
st.title("📄 PDF Upload to Azure Blob Storage")

# Load connection string from .env file
connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

# Sidebar for Azure credentials
st.sidebar.header("Azure Configuration")
if connection_string:
    st.sidebar.success("✅ Connection string loaded from .env file")
else:
    st.sidebar.warning("⚠️ Connection string not found in .env file")
    connection_string = st.sidebar.text_input(
        "Azure Storage Connection String (Optional Override)",
        type="password",
        help="Leave empty to use .env file, or enter connection string here"
    )

# Main content
col1, col2 = st.columns(2)

with col1:
    folder_name = st.text_input(
        "Enter Folder Name",
        placeholder="e.g., my-documents",
        help="The name of the folder to create in Azure Blob Storage"
    )

with col2:
    pdf_file = st.file_uploader(
        "Upload PDF File",
        type="pdf",
        help="Select a PDF file to upload"
    )

# Upload button
if st.button("📤 Upload PDF", use_container_width=True):
    # Validation
    if not connection_string:
        st.error("❌ Please provide Azure Storage connection string")
    elif not folder_name:
        st.error("❌ Please enter a folder name")
    elif not pdf_file:
        st.error("❌ Please select a PDF file")
    else:
        try:
            with st.spinner("⏳ Uploading to Azure Blob Storage..."):
                # Upload PDF using blob storage manager
                success, result = upload_pdf_to_blob(
                    connection_string,
                    folder_name,
                    pdf_file
                )
                
                if success:
                    # Success messages
                    st.success(f"✅ PDF uploaded successfully!")
                    st.success(f"📁 Folder: {result['folder_path']}")
                    st.success(f"📄 File: {result['file_name']}")
                    st.info(f"📍 Blob path: {result['blob_name']}")
                    
                    if result['container_created']:
                        st.info(f"✅ Created container: {result['container_name']}")
                else:
                    st.error(f"❌ Error uploading file: {result['error']}")
                    
        except Exception as e:
            st.error(f"❌ Error uploading file: {str(e)}")

# Footer with instructions
st.markdown("---")
st.markdown("""
### 📋 Instructions:
1. **Get Connection String**: Go to Azure Portal → Storage Account → Access Keys → Copy Connection String
2. **Paste Connection String**: Enter it in the sidebar on the left
3. **Enter Folder Name**: Provide a name for the folder (will be created if it doesn't exist)
4. **Upload PDF**: Select your PDF file and click Upload PDF

### 💡 Notes:
- Folders are created as blob path prefixes
- Files are organized in the `uploads` container
- Connection string is not saved and only used during upload
""")
