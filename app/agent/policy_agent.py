from langchain.agents import create_agent

from app.agent.llm import llm
from app.agent.prompt import POLICY_PROMPT
from app.tools.rag import rag_search


policy_agent = create_agent(
    model=llm,
    tools=[rag_search],
    system_prompt=POLICY_PROMPT,
)