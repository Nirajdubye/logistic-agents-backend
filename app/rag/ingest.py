import os
from sqlalchemy import text

from app.database.connection import SessionLocal
from app.rag.loader import load_documents_from_folder
from app.rag.chunker import chunk_text
from app.rag.embedder import embeddings

BASE_APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCS_FOLDER = os.path.join(BASE_APP_DIR, "policies", "docs")
if not os.path.exists(DOCS_FOLDER):
    DOCS_FOLDER = os.path.join("app", "policies", "docs")


def clear_source(db, source_file: str):
    """Safely delete existing chunks for a file before re-ingesting."""
    db.execute(
        text("DELETE FROM document_chunks WHERE source_file = :source_file"),
        {"source_file": source_file},
    )


def ingest():
    """Ingest governance PDF/TXT documents into PostgreSQL pgvector table."""
    print(f"Reading policy documents from: {os.path.abspath(DOCS_FOLDER)}")
    documents = load_documents_from_folder(DOCS_FOLDER)
    if not documents:
        print(f"No documents found in {DOCS_FOLDER}")
        return

    db = SessionLocal()
    try:
        for doc in documents:
            source_file = doc["source_file"]
            print(f"Processing {source_file} ...")

            clear_source(db, source_file)

            chunks = chunk_text(doc["content"])
            vectors = embeddings.embed_documents(chunks)

            for idx, (chunk, vector) in enumerate(zip(chunks, vectors)):
                db.execute(
                    text("""
                        INSERT INTO document_chunks
                            (source_file, chunk_index, content, embedding)
                        VALUES
                            (:source_file, :chunk_index, :content, CAST(:embedding AS vector))
                    """),
                    {
                        "source_file": source_file,
                        "chunk_index": idx,
                        "content": chunk,
                        "embedding": str(vector),
                    },
                )
            db.commit()
            print(f"  -> inserted {len(chunks)} chunks")
    finally:
        db.close()


if __name__ == "__main__":
    ingest()