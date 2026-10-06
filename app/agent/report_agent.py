from langchain.agents import create_agent

from app.agent.llm import llm
from app.agent.report_prompt import REPORT_PROMPT
from app.tools.report_langchain_tools import get_report_tools

report_agent = create_agent(
    model=llm,
    tools=get_report_tools(),
    system_prompt=REPORT_PROMPT,
)