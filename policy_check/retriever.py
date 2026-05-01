from policy_check.pipeline import embed_text
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
import os

load_dotenv()

ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
API_KEY = os.getenv("AZURE_SEARCH_KEY")
INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME")
credential = AzureKeyCredential(API_KEY)

###################################################################################################

def retrieve_relevant_chunks(question: str, top_k: int = 5) -> list:

    search_client = SearchClient(ENDPOINT, INDEX_NAME, credential)

    question_embedding = embed_text(question)

    vector_query = VectorizedQuery(
        vector=question_embedding,
        k_nearest_neighbors=top_k,
        fields="embedding"
    ) 

    results = search_client.search(
        search_text=question,        # keyword part
        vector_queries=[vector_query],  # semantic part
        select=["chunk_id", "text"],
        top=top_k
    )

    # ── Format Results ────────────────────────────────────────
    chunks = []
    for result in results:
        chunks.append({
            "chunk_id": result["chunk_id"],
            "text"    : result["text"],
            "score"   : result["@search.score"]
        })

    print(f" ✅ Retrieved {len(chunks)} relevant chunks.")
    return chunks