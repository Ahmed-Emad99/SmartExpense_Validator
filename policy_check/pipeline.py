from pypdf import PdfReader
from openai import AzureOpenAI
from dotenv import load_dotenv
import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from unstructured.partition.pdf import partition_pdf
from unstructured.chunking.title import chunk_by_title
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SearchableField,
    SemanticConfiguration,
    SemanticPrioritizedFields,
    SemanticField,
    SemanticSearch
)
from azure.core.credentials import AzureKeyCredential

load_dotenv()

# Extract base endpoint (remove /openai/deployments/... path)
full_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
base_endpoint = full_endpoint.split("/openai/deployments")[0] if "/openai/deployments" in full_endpoint else full_endpoint

client = AzureOpenAI(
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=base_endpoint,
    api_key=os.getenv("AZURE_OPENAI_KEY"),
)

ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
API_KEY = os.getenv("AZURE_SEARCH_KEY")
INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME")
credential = AzureKeyCredential(API_KEY)

#########################################################################################

def load_pdf(file_path: str) -> str:

    reader = PdfReader(file_path)
    full_text = []

    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            full_text.append(text.strip())

    print(f"Loaded {len(reader.pages)} pages from {file_path}")
    return "\n\n".join(full_text)

###############################################################################################

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> list:

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=[ "\n\n","\n", " ", ""],
        length_function=len,
    )

    chunks = splitter.split_text(text)

    return chunks

def chunking(file_path):

    elements = partition_pdf(file_path, strategy="hi_res")

    
    chunks = chunk_by_title(
        elements,
        max_characters=1500,        # hard max per chunk
        new_after_n_chars=1000,     # soft preferred size
        overlap=200,                # overlap on oversized splits
        overlap_all=False,          # don't overlap between normal chunks
        multipage_sections=True,    # allow sections to span pages
        combine_text_under_n_chars=500,  # combine small sections
    )

    clean_chunks = [chunk.text for chunk in chunks]

    return clean_chunks
    

###############################################################################################

def embed_text(text: str) -> list:
    """Embed a single text string. Returns a vector list."""
    response = client.embeddings.create(
        input=text,
        model=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
    )
    return response.data[0].embedding


def embed_chunks(chunks: list) -> list:
    
    embedded = []

    for i, chunk in enumerate(chunks):
        print(f"   Embedding chunk {i + 1}/{len(chunks)}...", end="\r")
        vector = embed_text(chunk)
        embedded.append({
            "chunk_id"  : f"chunk_{i}",
            "text"      : chunk,
            "embedding" : vector
        })
    
    print(f"\nEmbedded {len(embedded)} chunks.")
    return embedded

###############################################################################################

def create_index(embedding_dim: int = 3072):

    index_client = SearchIndexClient(ENDPOINT, credential)

    # Delete if already exists to ensure clean recreation
    existing = [idx.name for idx in index_client.list_indexes()]
    if INDEX_NAME in existing:
        print(f"✅ Index '{INDEX_NAME}' already exists — skipping creation.")
        return

    index = SearchIndex(
        name=INDEX_NAME,
        fields=[
            SimpleField(name="chunk_id",type=SearchFieldDataType.String,key=True),
            SearchableField(name="text",type=SearchFieldDataType.String),
            SearchField(name="embedding",type=SearchFieldDataType.Collection(SearchFieldDataType.Single),searchable=True,
                        vector_search_dimensions=embedding_dim,
                        vector_search_profile_name="myHnswProfile"
            )
        ],
        vector_search=VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="myHnsw")],
            profiles=[VectorSearchProfile(
                name="myHnswProfile",
                algorithm_configuration_name="myHnsw"
            )]
        ),
            semantic_search=SemanticSearch(
            configurations=[
                SemanticConfiguration(
                    name="default",
                    prioritized_fields=SemanticPrioritizedFields(
                        content_fields=[
                            SemanticField(field_name="text")
                        ]
                    )
                )
            ]
        )
    )
    
    index_client.create_index(index)
    print(f"✅ Index '{INDEX_NAME}' created.")

#######################################################################################

def store_chunks(embedded_chunks: list):
    """Upload embedded chunks to Azure AI Search."""
    search_client = SearchClient(ENDPOINT, INDEX_NAME, credential)

    # Format documents for upload
    documents = [
        {
            "chunk_id" : chunk["chunk_id"],
            "text"     : chunk["text"],
            "embedding": chunk["embedding"]
        }
        for chunk in embedded_chunks
    ]

    # Upload in batches of 100
    batch_size = 100
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        result = search_client.upload_documents(documents=batch)
        print(f"✅ Uploaded batch {i // batch_size + 1} "
              f"({len(batch)} chunks)")

    print(f"✅ All {len(documents)} chunks stored in Azure AI Search.")
