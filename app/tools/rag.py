from langchain.tools import tool
from app.services.policy_service import PolicyService


@tool
def rag_search(query: str, top_k: int = 5):
    """
    Search the company's Policy, SOP, Code of Conduct, and Rules knowledge base.

    PURPOSE:
    Retrieves the most relevant passages from the company's governance
    documents (Company Policies, Standard Operating Procedures, Code of
    Conduct, Company Rules & Regulations) using semantic vector search
    over document_chunks (pgvector).

    WHEN TO USE:
    Use this tool whenever the user asks how something works, what a
    policy/procedure/rule is, what a fee, deadline, or limit is, or
    anything about conduct and compliance standards.

    Do NOT use this for a specific live record (shipment, invoice,
    customer, driver, etc.) — use the operational database tools for that.

    Returns the top matching passages, each with its source document and
    a similarity score, so the answer can be grounded and cited.
    """
    service = PolicyService()
    return service.fetch(query, top_k)