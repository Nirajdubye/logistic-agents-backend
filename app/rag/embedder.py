import os
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()

EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-001")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

embeddings = GoogleGenerativeAIEmbeddings(
    model=EMBEDDING_MODEL,
    output_dimensionality=768,
    google_api_key=GEMINI_API_KEY,
)


def embed_query(query: str) -> list:
    """Embed a single search query string (used by PolicyService & rag_search tool)."""
    return embeddings.embed_query(query)


def embed_documents(texts: list) -> list:
    """Embed a list of document chunk strings (used by ingest.py)."""
    return embeddings.embed_documents(texts)