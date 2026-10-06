from langchain.agents import create_agent

from app.agent.llm import llm
from app.agent.email_prompt import EMAIL_PROMPT
from app.tools.email_langchain_tool import send_email_tool

email_agent = create_agent(
    model=llm,
    tools=[send_email_tool],
    system_prompt=EMAIL_PROMPT,
)