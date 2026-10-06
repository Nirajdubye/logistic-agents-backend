"""
Evaluates ANSWER quality, not just retrieval - using RAGAS, an LLM-judged
evaluation framework. This catches problems retrieval metrics can't see,
e.g. retrieval found the right chunk, but the model still hallucinated or
added something not actually in the text.

IMPORTANT: `response` here is policy_agent's actual generated answer (it
reads the retrieved chunks and writes a real answer to the question), NOT
the raw output of the rag_search tool. Using raw retrieved text as
"response" makes Faithfulness trivially 1.0 (text is always "faithful" to
itself) and makes FactualCorrectness misleadingly low (a short reference
sentence won't token-overlap well against several full raw chunks) -
neither number means what it's supposed to mean in that setup.

Requires: pip install ragas

Three metrics used here:
- Faithfulness: does the generated answer avoid claiming things NOT
  supported by the retrieved context? Low faithfulness = hallucination,
  even if retrieval itself was fine.
- LLMContextRecall: did the retrieved chunks contain everything needed to
  answer, compared against your reference_answer?
- FactualCorrectness: does the generated answer actually match your
  reference_answer's facts? (Requires reference_answer to be filled in
  for each item in golden_dataset.py.)

RAGAS uses an LLM as the "judge" - we reuse your existing Gemini setup so
no separate API/account is needed.

Run from backend/:
    python -m app.rag.eval.evaluate_generation
"""

import os
import sys
import types

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

# --------------------------------------------------------------------------
# Workaround for a known ragas bug (open, unassigned as of this writing:
# github.com/explodinggradients/ragas/issues/2753). ragas/llms/base.py
# unconditionally does:
#     from langchain_community.chat_models.vertexai import ChatVertexAI
# but that path was removed from newer langchain-community releases (moved
# to the separate langchain-google-vertexai package instead). This breaks
# `import ragas` for EVERYONE not using Google Vertex AI, regardless of
# which LLM you're actually evaluating with.
#
# Since we never use VertexAI here, we hand Python a fake, empty module
# under that exact name before ragas imports it. The import line succeeds;
# the stub class is never actually constructed or used at runtime because
# our evaluator_llm is ChatGoogleGenerativeAI, not ChatVertexAI.
# --------------------------------------------------------------------------
if "langchain_community.chat_models.vertexai" not in sys.modules:
    try:
        import langchain_community.chat_models.vertexai  # noqa: F401
    except ModuleNotFoundError:
        _stub = types.ModuleType("langchain_community.chat_models.vertexai")

        class ChatVertexAI:  # placeholder only - never instantiated
            def __init__(self, *args, **kwargs):
                raise RuntimeError(
                    "ChatVertexAI is a stub (Vertex AI is not configured in "
                    "this project) - this should never actually be called."
                )

        _stub.ChatVertexAI = ChatVertexAI
        sys.modules["langchain_community.chat_models.vertexai"] = _stub

from ragas import evaluate, EvaluationDataset
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import Faithfulness, LLMContextRecall, FactualCorrectness

from app.rag.eval.golden_dataset import GOLDEN_DATASET
from app.rag.eval.evaluate_retrieval import retrieve
from app.agent.policy_agent import policy_agent  # the actual agent that reads context and writes an answer
from app.agent.utils import extract_text

load_dotenv()

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

judge_llm = ChatGoogleGenerativeAI(
    model=MODEL_NAME,
    google_api_key=os.getenv("GEMINI_API_KEY"),
)
evaluator_llm = LangchainLLMWrapper(judge_llm)


def build_dataset():
    samples = []
    for item in GOLDEN_DATASET:
        question = item["question"]

        # Same retrieval call as evaluate_retrieval.py, so contexts here
        # match exactly what the real system actually retrieves - this is
        # what RAGAS checks the generated answer's faithfulness against.
        rows = retrieve(question)
        contexts = [row[1] for row in rows]  # chunk content column

        # Call the ACTUAL agent (not the raw tool) so it reads those chunks
        # and writes a real answer - this is what makes Faithfulness and
        # FactualCorrectness measure something meaningful, instead of
        # comparing raw retrieved text against itself.
        result = policy_agent.invoke({"messages": [{"role": "user", "content": question}]})
        answer = extract_text(result["messages"][-1])

        samples.append({
            "user_input": question,
            "retrieved_contexts": contexts,
            "response": answer,
            "reference": item.get("reference_answer", ""),
        })
        print(f"[eval] Built sample for: {question}")
        print(f"        generated answer: {answer[:150]}{'...' if len(answer) > 150 else ''}")

    return EvaluationDataset.from_list(samples)


def run():
    if not GOLDEN_DATASET:
        print("GOLDEN_DATASET is empty - add questions to golden_dataset.py first.")
        return

    dataset = build_dataset()

    print("\nRunning RAGAS evaluation (this calls the judge LLM once per "
          "metric per question - may take a minute for a larger dataset)...\n")

    result = evaluate(
        dataset=dataset,
        metrics=[Faithfulness(), LLMContextRecall(), FactualCorrectness()],
        llm=evaluator_llm,
    )

    print(result)

    df = result.to_pandas()
    out_path = "rag_eval_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\nPer-question breakdown saved to {out_path}")


if __name__ == "__main__":
    run()