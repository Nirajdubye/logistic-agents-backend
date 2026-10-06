from langchain.agents import create_agent

from app.agent.llm import llm
from app.agent.prompt import OPERATIONAL_PROMPT

from app.tools.customer_tools import customer_lookup
from app.tools.shipment_tools import get_shipment_status
from app.tools.driver_tool import get_driver_details
from app.tools.warehouse_receipt_tools import get_warehouse_receipt_details
from app.tools.cargo_release_tools import get_cargo_release_details
from app.tools.invoice_tools import get_invoice_details
from app.tools.quotation_tools import get_quotation_details
from app.tools.email_tools import send_email_notification


operational_agent = create_agent(
    model=llm,
    tools=[
        customer_lookup,
        get_shipment_status,
        get_driver_details,
        get_warehouse_receipt_details,
        get_cargo_release_details,
        get_invoice_details,
        get_quotation_details,
        send_email_notification,
    ],
    system_prompt=OPERATIONAL_PROMPT,
)
