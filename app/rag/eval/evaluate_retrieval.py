"""
Evaluates ONLY retrieval quality - does pgvector's nearest-neighbor search
surface the correct document for each question? No LLM judge needed here;
this is pure "did the right file show up in the top-k results" math.

Two standard metrics:

- Hit Rate@k: of all questions, what fraction had the correct source file
  ANYWHERE in the top k results? (0.8 = 80% of questions found their answer
  somewhere in the top k chunks retrieved)

- MRR (Mean Reciprocal Rank): rewards finding the right answer EARLIER, not
  just somewhere in top-k. If the correct file is rank 1, that question
  scores 1.0. Rank 2 scores 0.5. Rank 5 scores 0.2. Not found = 0. Average
  across all questions. A high Hit Rate but low MRR means retrieval finds
  the right document but buries it near the bottom of top-k - worth
  tuning chunk size or top_k in that case.

Run from backend/:
    python -m app.rag.eval.evaluate_retrieval
"""

from sqlalchemy import text
from app.rag.embedder import embed_query
from app.database.connection import SessionLocal
from app.rag.eval.golden_dataset import GOLDEN_DATASET

TOP_K = 5


def retrieve(query: str, top_k: int = TOP_K):
    query_vector = embed_query(query)
    embedding_str = "[" + ",".join(str(v) for v in query_vector) + "]"

    db = SessionLocal()
    try:
        result = db.execute(
            text("""
                SELECT source_file, content, 1 - (embedding <=> :embedding) AS similarity
                FROM document_chunks
                ORDER BY embedding <=> :embedding
                LIMIT :top_k
            """),
            {"embedding": embedding_str, "top_k": top_k},
        )
        return result.fetchall()
    finally:
        db.close()


def evaluate():
    if not GOLDEN_DATASET:
        print("GOLDEN_DATASET is empty - add questions to golden_dataset.py first.")
        return

    hits = 0
    reciprocal_ranks = []

    print(f"Evaluating {len(GOLDEN_DATASET)} questions at top_k={TOP_K}...\n")

    for item in GOLDEN_DATASET:
        question = item["question"]
        expected_file = item["expected_source_file"]

        rows = retrieve(question)
        retrieved_files = [row[0] for row in rows]

        rank = None
        for i, source_file in enumerate(retrieved_files, start=1):
            if source_file == expected_file:
                rank = i
                break

        hit = rank is not None
        hits += int(hit)
        reciprocal_ranks.append(1 / rank if hit else 0)

        status = f"HIT  (rank {rank})" if hit else "MISS"
        print(f"[{status}] {question}")
        print(f"         expected: {expected_file}")
        print(f"         got:      {retrieved_files}\n")

    n = len(GOLDEN_DATASET)
    hit_rate = hits / n
    mrr = sum(reciprocal_ranks) / n

    print("=" * 60)
    print(f"Hit Rate@{TOP_K}: {hit_rate:.1%}  ({hits}/{n} questions found their document)")
    print(f"MRR@{TOP_K}:      {mrr:.3f}  (1.0 = always rank 1, 0 = never found)")
    print("=" * 60)

    if hit_rate < 0.8:
        print(
            "\nHit Rate below 80% - consider: smaller/more focused chunks, "
            "increasing top_k, or checking whether questions use very "
            "different wording than the source documents."
        )
    elif mrr < hit_rate - 0.15:
        print(
            "\nHit Rate is fine but MRR is noticeably lower - the right "
            "document is usually found, but often buried below rank 1. "
            "Consider re-ranking, or checking if chunks are too large/generic."
        )


if __name__ == "__main__":
    evaluate()