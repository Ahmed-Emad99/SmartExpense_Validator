import streamlit as st
import os
import time
from config import AzureConfig
from blob_storage import BlobStorageService
from doc_intelligence import DocumentIntelligenceService
from doc_processor import DocumentProcessor
from search_service import AzureSearchService
from rag_service import RAGService
from chat_service import ChatService


# ============================================================================
# CONFIGURATION AND INITIALIZATION
# ============================================================================

def initialize_services():
    """Initialize all services"""
    config = AzureConfig()
    
    # Initialize services
    blob_service = BlobStorageService(config.storage_connection_string)
    doc_service = DocumentIntelligenceService(
        config.doc_intelligence_endpoint,
        config.doc_intelligence_key
    )
    search_service = AzureSearchService(
        config.search_endpoint,
        config.search_key,
        config.search_index_name
    )
    
    # Create index if doesn't exist
    try:
        search_service.create_index()
    except:
        pass
    
    rag_service = RAGService(search_service)
    
    chat_service = ChatService(
        rag_service,
        azure_endpoint=config.azure_openai_endpoint,
        azure_key=config.azure_openai_key,
        api_version=config.azure_openai_api_version,
        model=config.azure_openai_model
    )
    
    processor = DocumentProcessor(chunk_size=2000, chunk_overlap=300)
    
    return {
        "config": config,
        "blob_service": blob_service,
        "doc_service": doc_service,
        "search_service": search_service,
        "rag_service": rag_service,
        "chat_service": chat_service,
        "processor": processor
    }


def setup_page():
    """Configure page settings"""
    st.set_page_config(
        page_title="PDF Chat with RAG",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.title("💬 PDF Chat with RAG")
    st.markdown("Upload PDFs and chat directly with their content using AI Search")


# ============================================================================
# SESSION STATE MANAGEMENT
# ============================================================================

def initialize_session_state():
    """Initialize Streamlit session state"""
    if "services" not in st.session_state:
        st.session_state.services = initialize_services()
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    if "current_document" not in st.session_state:
        st.session_state.current_document = None
    
    if "indexed_documents" not in st.session_state:
        st.session_state.indexed_documents = []


# ============================================================================
# UI COMPONENTS
# ============================================================================

def display_sidebar():
    """Display sidebar with upload and document selection"""
    with st.sidebar:
        st.header("📁 Document Management")
        
        # Upload section
        st.subheader("Upload New PDF")
        uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
        folder_name = st.text_input("Folder name (optional)", value="documents")
        
        if uploaded_file and st.button("Upload & Index", use_container_width=True):
            try:
                # Stage 1: Upload to blob storage
                st.info("📤 Stage 1/5: Uploading PDF to Azure Blob Storage...")
                services = st.session_state.services
                upload_info = services["blob_service"].upload_pdf(uploaded_file, folder_name)
                st.success("✅ PDF uploaded")
                
                # Stage 2: Generate SAS URL
                st.info("🔐 Stage 2/5: Generating access URL...")
                sas_url = services["blob_service"].get_blob_sas_url(upload_info["blob_name"])
                st.success("✅ Access URL generated")
                
                # Stage 3: Extract text with Document Intelligence
                st.info("📖 Stage 3/5: Extracting text from PDF (this may take 10-30 seconds)...")
                doc_result = services["doc_service"].analyze_document(sas_url)
                pages_data = services["doc_service"].extract_text_by_page(doc_result)
                total_chars = sum(len(p["text"]) for p in pages_data)
                st.success(f"✅ Text extracted ({total_chars} characters across {len(pages_data)} pages)")
                
                # Stage 4: Process into chunks (page by page)
                st.info("✂️ Stage 4/5: Processing document into chunks...")
                st.write(f"📊 Document size: {total_chars:,} characters across {len(pages_data)} pages")
                
                chunk_start = time.time()
                all_chunks = []
                for page_info in pages_data:
                    page_chunks = services["processor"].chunk_text(
                        page_info["text"],
                        uploaded_file.name,
                        page_number=page_info["page_number"]
                    )
                    all_chunks.extend(page_chunks)
                
                chunk_time = time.time() - chunk_start
                chunks = all_chunks
                
                st.write(f"✅ Created {len(chunks)} chunks in {chunk_time:.2f}s")
                if chunk_time > 5:
                    st.warning(f"⚠️ Chunking took {chunk_time:.2f}s - consider increasing chunk_size")
                st.success("✅ Chunking complete")
                
                # Debug: Show chunk page distribution
                with st.expander("📊 Chunk Distribution by Page"):
                    page_chunks = {}
                    for chunk in chunks:
                        page = chunk.page_number
                        page_chunks[page] = page_chunks.get(page, 0) + 1
                    
                    for page in sorted(page_chunks.keys()):
                        st.write(f"Page {page}: {page_chunks[page]} chunks")
                
                # Stage 5: Index in Azure AI Search
                index_start = time.time()
                documents = services["processor"].prepare_for_indexing(chunks)
                prep_time = time.time() - index_start
                st.info(f"Prepared {len(documents)} documents in {prep_time:.2f}s")
                
                st.info(f"🔍 Stage 5/5: Indexing {len(documents)} chunks in Azure AI Search (this may take time)...")
                index_time = time.time()
                result = services["search_service"].index_documents(documents)
                total_index_time = time.time() - index_time
                st.success(f"✅ Indexing complete in {total_index_time:.2f}s")
                
                # Update indexed documents list
                st.session_state.indexed_documents = services["search_service"].get_all_sources()
                st.session_state.current_document = uploaded_file.name
                
                st.success(f"✅ Document indexed successfully! {result['successful']} chunks indexed.")
                st.info(f"📊 Total chunks: {result['total_documents']}")
                    
            except Exception as e:
                st.error(f"Error processing document: {str(e)}")
        
        st.markdown("---")
        
        # Document selection
        st.subheader("📚 Select Document")
        services = st.session_state.services
        available_docs = services["search_service"].get_all_sources()
        
        if available_docs:
            selected_doc = st.selectbox(
                "Choose a document to chat with:",
                available_docs,
                index=0 if not st.session_state.current_document else (
                    available_docs.index(st.session_state.current_document)
                    if st.session_state.current_document in available_docs else 0
                )
            )
            st.session_state.current_document = selected_doc
        else:
            st.info("No documents indexed yet. Upload a PDF to get started!")
        
        st.markdown("---")
        
        # Chat settings
        st.subheader("⚙️ Chat Settings")
        top_k = st.slider("Number of context chunks to retrieve:", 1, 10, 5)
        
        st.markdown("---")
        
        # Clear chat history
        if st.button("🔄 Clear Chat History", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()
        
        st.markdown("---")
        
        # Debug section
        if st.checkbox("🔍 Debug: Inspect Azure Search"):
            st.subheader("Azure Search Index Contents")
            services = st.session_state.services
            current_doc = st.session_state.current_document
            
            if current_doc:
                try:
                    # Search for all chunks from current document
                    results = services["search_service"].search_client.search(
                        search_text="*",
                        filter=f"source_file eq '{current_doc}'",
                        top=100,
                        select=["id", "page_number", "source_file", "chunk_index"]
                    )
                    
                    chunks_info = []
                    for result in results:
                        chunks_info.append({
                            "id": result["id"],
                            "page_number": result.get("page_number", "N/A"),
                            "chunk_index": result.get("chunk_index", "N/A")
                        })
                    
                    if chunks_info:
                        st.write(f"Found {len(chunks_info)} chunks:")
                        for chunk in chunks_info:
                            st.write(f"  • {chunk['id']} - Page {chunk['page_number']}, Chunk {chunk['chunk_index']}")
                    else:
                        st.write("No chunks found in index")
                        
                except Exception as e:
                    st.error(f"Error reading index: {str(e)}")


def display_chat_interface():
    """Display main chat interface"""
    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask a question about the document..."):
        # Add user message to history
        st.session_state.chat_history.append({
            "role": "user",
            "content": prompt
        })
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response
        with st.chat_message("assistant"):
            try:
                services = st.session_state.services
                
                # Get current document selection
                current_doc = st.session_state.current_document
                
                # Get RAG response
                response = services["chat_service"].chat_with_rag(
                    user_query=prompt,
                    chat_history=st.session_state.chat_history[:-1],
                    source_file=current_doc,
                    top_k=5
                )
                
                # Display answer
                st.markdown(response["answer"])
                
                # Display sources in expander
                with st.expander("📚 View Sources"):
                    sources_text = services["chat_service"].format_sources_for_display(
                        response["sources"]
                    )
                    st.markdown(sources_text)
                    
                    st.markdown("**Tokens Used:**")
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Prompt", response["tokens_used"]["prompt"])
                    col2.metric("Completion", response["tokens_used"]["completion"])
                    col3.metric("Total", response["tokens_used"]["total"])
                
                # Add assistant response to history
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": response["answer"]
                })
                
            except Exception as e:
                st.error(f"Error generating response: {str(e)}")


def display_azure_configuration():
    """
    Display Azure configuration status in sidebar
    
    Returns:
        AzureConfig: Configuration object
    """
    config = st.session_state.services["config"]
    
    return config


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application entry point"""
    # Setup page
    setup_page()
    
    # Initialize session state
    initialize_session_state()
    
    # Display sidebar
    display_sidebar()
    
    # Display chat interface
    display_chat_interface()


if __name__ == "__main__":
    main()