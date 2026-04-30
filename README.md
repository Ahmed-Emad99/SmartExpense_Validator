# SmartExpense Validator - Merged with RAG

This is the **integrated SmartExpense Validator** project, which now combines:
1. **Invoice Processing & Validation** (original SmartExpense project)
2. **Travel Policy Chatbot with RAG** (from rag-policy project)

## Project Structure

```
SmartExpense_Validator-main/
├── app.py                               # Main Streamlit application
├── requirements.txt                     # All dependencies
├── README.md                            # This file
├── .env                                 # Azure credentials (do not commit)
├── .gitignore
│
├── models/
│   ├── __init__.py
│   ├── invoice_model.py                # Invoice data schema
│   └── chat_model.py                   # Travel session & chat schemas
│
├── services/
│   ├── __init__.py
│   ├── config.py                       # Azure configuration
│   ├── blob_storage_service.py         # Azure Blob Storage operations
│   │
│   ├── invoice/                        # Invoice processing package
│   │   ├── __init__.py
│   │   ├── invoice_processor.py        # Invoice extraction & processing
│   │   ├── validation_service.py       # 2-layer invoice validation
│   │   └── azure_document_service.py   # Document Intelligence API
│   │
│   └── policy_rag/                     # Policy & RAG package
│       ├── __init__.py
│       ├── chat_service.py             # Chat with RAG context
│       ├── rag_service.py              # RAG operations
│       ├── search_service.py           # Azure AI Search
│       ├── doc_processor.py            # Document chunking
│       └── doc_intelligence_service.py # PDF text extraction
│
├── utils/
│   ├── __init__.py
│   ├── helpers.py                      # UI components & utilities
│   └── date_helpers.py                 # Date validation & deadline management
│
└── docs/
    └── Comprehensive Corporate Travel.pdf  # Travel policy document
```

## Architecture

### Service Organization

The `services/` package is organized into two logical subpackages:

**Invoice Package** (`services.invoice/`)
```python
from services.invoice.invoice_processor import InvoiceProcessor
from services.invoice.validation_service import ValidationService
from services.invoice.azure_document_service import AzureDocumentService
```
Handles all invoice extraction, validation, and processing logic.

**Policy RAG Package** (`services.policy_rag/`)
```python
from services.policy_rag.chat_service import ChatService
from services.policy_rag.rag_service import RAGService
from services.policy_rag.search_service import AzureSearchService
from services.policy_rag.doc_processor import DocumentProcessor
from services.policy_rag.doc_intelligence_service import DocumentIntelligenceService
```
Handles policy document management, indexing, and LLM-powered Q&A.

**Shared Services** (`services/`)
```python
from services.config import AzureConfig
from services.blob_storage_service import BlobStorageService
```
Core infrastructure used by both packages.

## Features

### Invoice Processing
- **Automated Extraction**: Uses Azure Document Intelligence to extract invoice data
- **Multi-Format Support**: Handles PDF and image uploads
- **2-Layer Validation**: Completeness checks + business rule validation
- **Duplicate Detection**: Prevents duplicate expense submissions
- **Currency Consistency**: Ensures all invoices in a trip use the same currency
- **Archive**: Valid invoices automatically stored in Azure Blob Storage

### Policy Chatbot with RAG
- **Real-Time Q&A**: Ask questions about travel policies
- **Policy Indexing**: Upload and index PDF policy documents
- **Context-Aware Responses**: LLM generates answers grounded in actual policies
- **Source References**: Chat answers include page numbers and document references
- **Persistent History**: Chat history maintained across sessions



### Invoice Processing Workflow
```
User Inputs Travel Dates
    ↓
Upload Invoices (PDF/Image)
    ↓
Extract Data (Azure Document Intelligence)
    ↓
Validate (Layer 1: Completeness, Layer 2: Business Rules)
    ↓
Archive to Azure Blob Storage (if valid)
    ↓
Review & Upload Replacements (if needed)
    ↓
Final Summary with Extracted Data
```

### Policy Chat with RAG Workflow
```
User Asks Question About Policy
    ↓
RAG Service Searches Policy Index
    ↓
Retrieve Top 5 Relevant Document Chunks
    ↓
Send Query + Context to Azure OpenAI
    ↓
Generate Answer Grounded in Policy
    ↓
Display Answer + Source References
```

## Configuration

All Azure services are configured via `.env` file:

```env
# Invoice Processing
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=...
AZURE_DOCUMENT_INTELLIGENCE_KEY=...
AZURE_STORAGE_CONNECTION_STRING=...

# Policy Chatbot with RAG
AZURE_SEARCH_ENDPOINT=...
AZURE_SEARCH_KEY=...
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_KEY=...
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

## Getting Started

### Prerequisites
- Python 3.10+
- Azure Account with:
  - Document Intelligence service
  - Blob Storage account
  - AI Search service
  - OpenAI service (GPT-4o model)

### 1. Clone & Setup Environment
```bash
# Clone repository
git clone <repo-url>
cd SmartExpense_Validator-main

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Azure Credentials
```bash
# Update .env with your Azure credentials
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=your-key
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;...
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net/
AZURE_SEARCH_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_KEY=your-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

### 3. Run Application
```bash
streamlit run app.py
```

Visit `http://localhost:8501`

## Usage

### Submitting Expenses
1. Enter your travel dates
2. Upload invoice images or PDFs
3. System automatically extracts: date, vendor, total, items, tax ID, currency
4. Validates against:
   - Completeness (has all required fields)
   - Travel window (invoice date within trip)
   - Upload deadline (within 30 days of return)
   - Currency consistency (all invoices same currency)
   - Duplicates (same date, total, vendor, items)
5. Valid invoices archived to Azure Blob Storage
6. Can re-upload replacements for invalid invoices

### Using Policy Chatbot
1. Sidebar: "💬 Policy Assistant"
2. Ask any question about company travel policy
3. RAG retrieves relevant policy sections
4. LLM generates accurate, policy-grounded answer
5. View source documents and page references

## Validation Rules

### Layer 1: Field Completeness
- Must have invoice date
- Must have total price
- Must have at least one purchased item

### Layer 2: Business Rules
- Invoice date must fall within travel dates
- Must be uploaded within 30 days of return
- Currency must be consistent across session
- No duplicate invoices (same date + total + items + vendor)

## Data Models

### InvoiceData
```python
invoice_id: str
date: Optional[str]         # YYYY-MM-DD
total_price: Optional[float]
currency: Optional[str]     # ISO code (USD, EUR, etc)
purchased_items: List[str]
vendor_name: Optional[str]
tax_number: Optional[str]
is_valid: bool
validation_message: str
```

### TravelSession
```python
travel_start: date
travel_end: date
upload_deadline: date       # travel_end + 30 days
is_within_upload_window: bool  # property
```

## Azure Services Used

| Service | Purpose |
|---------|---------|
| Azure Document Intelligence | Extract text from invoices and PDFs |
| Azure Blob Storage | Archive valid invoices |
| Azure AI Search | Index and search policy documents |
| Azure OpenAI (GPT-4o) | Generate policy answers with RAG |

## Troubleshooting

### "RAG services unavailable"
- Check Azure configuration in `.env`
- Verify search endpoint and credentials
- Ensure OpenAI endpoint is correct

### "Failed to index policy document"
- Ensure Azure AI Search service exists
- Check search credentials
- Verify index name is correct

### Invoice validation errors
- Date format must be YYYY-MM-DD
- All prices must be numbers
- Currency codes must be ISO format (USD, EUR, GBP, etc)

## Development & Contributing

### Code Organization
- **Models** - Pydantic data schemas for type safety
- **Services** - Business logic organized by domain
  - `invoice/` - All invoice processing logic
  - `policy_rag/` - All RAG and chatbot logic
- **Utils** - Helper functions and utilities

### Running the Application
```bash
# Development server with auto-reload
streamlit run app.py

# Production with gunicorn (when ready)
gunicorn -w 1 -b 0.0.0.0:8000 "streamlit.web.cli:main --server.port=8000"
```

### Project Notes
- All services are cached using `@st.cache_resource` for performance
- RAG uses keyword search (can be upgraded to semantic search)
- Document chunks: 2000 characters with 300-char overlap
- Top-k retrieval: 5 chunks per query (configurable in services)

### Future Enhancements
- [ ] Add comprehensive test suite (unit & integration)
- [ ] Docker containerization
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Multi-language policy support
- [ ] Semantic search instead of keyword search
- [ ] Expense category classification
- [ ] Budget tracking and alerts
- [ ] Historical trip reports
- [ ] Mobile app
- [ ] Integration with accounting systems
- [ ] User authentication & role-based access
- [ ] REST API endpoints

## Support & Documentation

- **Project README**: [MERGED_PROJECT_README.md](MERGED_PROJECT_README.md)
- **Travel Policy**: [docs/Comprehensive Corporate Travel.pdf](docs/Comprehensive%20Corporate%20Travel.pdf)
- **Issues**: Report via GitHub Issues

## License

[Add your license here]

---

**Project Created:** April 30, 2026  
**Version:** 2.1  
**Status:** Production Ready  
**Maintainers:** [Your Team]
