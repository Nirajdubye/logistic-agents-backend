from sqlalchemy import text
from app.database.connection import SessionLocal
from app.rag.embedder import embeddings
import time

class PolicyService:

    def __init__(self):
        self.db = SessionLocal()

    def close(self):
        self.db.close()

    ####################################################################
    # Semantic Search over document_chunks
    ####################################################################

    def search(self, query: str, top_k: int = 5):
        t0 = time.perf_counter()
        query_vector = embeddings.embed_query(query)
        print(f"[TIMING] embed_query took {time.perf_counter() - t0:.2f}s")

        t1 = time.perf_counter()
        sql = text("""
            SELECT
                source_file,
                chunk_index,
                content,
                1 - (embedding <=> CAST(:qvec AS vector)) AS similarity
            FROM document_chunks
            ORDER BY embedding <=> CAST(:qvec AS vector)
            LIMIT :top_k
        """)

        rows = self.db.execute(
            sql,
            {"qvec": str(query_vector), "top_k": top_k},
        ).mappings().all()

        return [dict(r) for r in rows]

    ####################################################################
    # Unified Public Entry Point
    ####################################################################

    def fetch(self, query: str, top_k: int = 5):
        try:
            results = self.search(query, top_k)
            if not results:
                return {
                    "success": False,
                    "message": "No relevant policy or procedure information found."
                }
            return {
                "success": True,
                "query": query,
                "results": results,
            }
        finally:
            self.close()