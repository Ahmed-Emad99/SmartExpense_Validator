# PDF Chat with RAG - AI Search Application

A powerful Streamlit application that enables intelligent conversations with PDF documents using Retrieval-Augmented Generation (RAG) powered by Azure AI Search and OpenAI.

## Features

✨ **RAG-Powered Chat**
- Upload PDFs and automatically index them in Azure AI Search
- Chat directly with documents using natural language queries
- Keyword-based semantic search with context retrieval
- View source documents and relevance scores for transparency

🔍 **Intelligent Document Processing**
- Automatic text extraction using Azure Document Intelligence
- Smart document chunking with overlapping context windows
- Organized file structure with folder management

🤖 **AI-Powered Responses**
- Uses OpenAI's GPT-3.5-turbo for intelligent responses
- Context-aware answers based on indexed content
- Conversation history tracking
- Token usage tracking

☁️ **Azure Integration**
- Azure Blob Storage for document management
- Azure AI Search for efficient indexing and retrieval
- Azure Document Intelligence for OCR and text extraction

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Frontend                        │
│         (Chat Interface & Document Management)               │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌──────────────┐  ┌─────────────┐  ┌──────────────┐
│   Blob       │  │ Document    │  │ Chat Service │
│  Storage     │  │ Intelligence│  │ (RAG Logic)  │
└──────────────┘  └─────────────┘  └──────┬───────┘
        ▲                                  │
        │                    ┌─────────────┘
        │                    ▼
        │           ┌──────────────────┐
        └───────────│ Azure AI Search  │
                    │ (Indexing &      │
                    │  Retrieval)      │
                    └──────────────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  OpenAI GPT-3.5  │
                    │  (LLM Responses) │
                    └──────────────────┘
```

## Project Structure

```
.
├── app.py                   # Main Streamlit application
├── config.py               # Configuration & credentials management
├── blob_storage.py         # Azure Blob Storage service
├── doc_intelligence.py     # Azure Document Intelligence service
├── doc_processor.py        # Document chunking & processing
├── search_service.py       # Azure AI Search operations
├── rag_service.py          # RAG retrieval logic
├── chat_service.py         # Chat interface & LLM integration
├── requirements.txt        # Python dependencies
├── .env.example           # Example environment variables
└── README.md              # This file
```

## Prerequisites

- Python 3.8 or higher
- Azure Storage Account
- Azure Document Intelligence resource
- Azure AI Search service
- OpenAI API key

## Installation

1. **Clone or navigate to the project directory**
```bash
cd "c:\Users\Hasan Nader\Desktop\final project\ai search"
```

2. **Create a virtual environment**
```bash
python -m venv venv
venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

## Setup & Configuration

### 1. Create `.env` file

Create a `.env` file in the project root with the following environment variables:

```
# Azure Storage
AZURE_STORAGE_CONNECTION_STRING=your_connection_string

# Azure Document Intelligence
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://<region>.api.cognitive.microsoft.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=your_key

# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://<service-name>.search.windows.net/
AZURE_SEARCH_KEY=your_key

# OpenAI
OPENAI_API_KEY=your_key
OPENAI_ENDPOINT=https://api.openai.com/v1
OPENAI_API_VERSION=2024-02-15-preview
```

### 2. Azure Storage Account Setup

1. Go to [Azure Portal](https://portal.azure.com/)
2. Create or select a Storage Account
3. Go to **Access Keys** → Copy **Connection String**
4. Add to `.env` file

### 3. Azure Document Intelligence Setup

1. Create a Document Intelligence resource in Azure Portal
2. Go to **Keys and Endpoint**
3. Copy **Endpoint URL** and **API Key**
4. Add to `.env` file

### 4. Azure AI Search Setup

1. Create an Azure AI Search service in Azure Portal
2. Go to **Keys** section
3. Copy **Endpoint URL** and **Primary Admin Key**
4. Add to `.env` file

### 5. OpenAI Setup

1. Go to [OpenAI API](https://platform.openai.com/)
2. Create an API key
3. Add to `.env` file

## Running the Application

```bash
streamlit run app.py
```

The app will open in your default browser at `http://localhost:8501`

## Usage

### Step 1: Upload & Index a PDF

1. Enter a folder name (optional, defaults to "documents")
2. Click **Choose a PDF file** and select your document
3. Click **Upload & Index**
4. Wait for processing (extraction + chunking + indexing)

### Step 2: Chat with the Document

1. The document will automatically be selected
2. Type your question in the chat input
3. The AI will retrieve relevant content and generate an answer
4. View sources and relevance scores in the expandable section

### Step 3: Manage Documents

- **Select Document**: Choose which document to chat with from the sidebar
- **Clear Chat History**: Start a fresh conversation
- **Adjust Settings**: Control the number of context chunks retrieved

## How It Works

### Document Upload & Processing Flow

```
PDF Upload
    ↓
Upload to Azure Blob Storage
    ↓
Extract Text with Document Intelligence
    ↓
Chunk Text (1000 char chunks with 200 char overlap)
    ↓
Index Chunks in Azure AI Search
    ↓
Ready for Chat!
```

### Chat & Retrieval Flow

```
User Question
    ↓
Keyword Search in Azure AI Search
    ↓
Retrieve Top-5 Relevant Chunks
    ↓
Format Context from Retrieved Chunks
    ↓
Send to GPT-3.5 with System Prompt
    ↓
Generate and Display Answer
    ↓
Show Source Documents & Scores
```

## Configuration Options

### Document Processor Settings

Edit `doc_processor.py` to adjust:
- `chunk_size`: Size of each text chunk (default: 1000 characters)
- `chunk_overlap`: Overlap between chunks (default: 200 characters)

### Chat Settings

In the Streamlit sidebar:
- **Top-K Context**: Number of relevant chunks to retrieve (1-10)
- **Document Filter**: Select specific document or search all

## Features Detail

### Keyword Search (Current)
- Uses Azure AI Search's full-text search capabilities
- Efficient for straightforward queries
- Fast retrieval times

### Future: Semantic Search
- Will use embeddings-based search
- Better for meaning-based queries
- More contextual understanding

## Error Handling

- **Missing Credentials**: Check that all environment variables are set in `.env`
- **Index Creation Failed**: Ensure Azure AI Search service is accessible
- **Document Processing Error**: Verify PDF is readable and not corrupted
- **Chat Generation Error**: Check OpenAI API key and rate limits

## Troubleshooting

### "Index already exists" warning
- This is normal on subsequent runs
- The index will be reused for new documents

### Slow Performance
- Adjust `top_k` value in sidebar to retrieve fewer chunks
- Check Azure AI Search quotas

### Empty Search Results
- Ensure document was successfully indexed
- Check Azure AI Search index status in portal

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `AZURE_STORAGE_CONNECTION_STRING` | Blob Storage connection | `DefaultEndpointsProtocol=https;...` |
| `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` | Doc Intelligence URL | `https://westus.api.cognitive.microsoft.com/` |
| `AZURE_DOCUMENT_INTELLIGENCE_KEY` | Doc Intelligence API key | `your-32-char-key` |
| `AZURE_SEARCH_ENDPOINT` | AI Search URL | `https://myservice.search.windows.net/` |
| `AZURE_SEARCH_KEY` | AI Search API key | `your-key` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |

## Limitations

- Keyword search only (semantic search coming soon)
- Single document selection at a time
- Limited to GPT-3.5-turbo model (configurable)
- Index must be recreated for document updates

## Future Enhancements

- [ ] Semantic search using embeddings
- [ ] Multi-document chat
- [ ] Support for other file types (DOCX, TXT, images)
- [ ] Fine-tuning with document-specific data
- [ ] Chat history persistence
- [ ] Export conversation feature
- [ ] Document summarization

## License

This project is open source and available under the MIT License.
- **Upload Failure**: Detailed error messages will help troubleshoot

## Security Notes

⚠️ **Important**:
- Never commit your connection string to version control
- Use `.env` files locally and add to `.gitignore`
- Connection strings entered in the UI are not saved
- For production, consider using Azure Managed Identity or other secure authentication methods

## Troubleshooting

### "Invalid connection string"
- Verify the connection string from Azure Portal
- Ensure it hasn't expired
- Check for extra spaces or characters

### "Container already exists"
- This is normal if you've run the app before
- The app will skip creation and continue

### File not uploading
- Ensure the PDF file is valid
- Check Azure Storage account permissions
- Verify network connectivity to Azure

## Dependencies

- **streamlit**: Web app framework
- **azure-storage-blob**: Azure Blob Storage SDK

## License

This project is open source and available for modification and distribution.

## Support

For issues or questions about Azure Blob Storage, visit the [Azure Documentation](https://docs.microsoft.com/en-us/azure/storage/blobs/).
