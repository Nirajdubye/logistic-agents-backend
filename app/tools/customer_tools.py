from langchain_core.tools import tool
from app.services.customer_service import CustomerService


@tool
def customer_lookup(
    customer_identifier: str,
    relation: str = "customer",
):
    """
    Retrieves customer information and every business object connected to that customer.

    Use this tool whenever the user asks about a customer, company,
    invoices, shipments, quotations, warehouse receipts,
    pickup orders or invoice payments.

    Supported customer identifiers:
    • Customer Code (e.g. PGL1063)
    • Company Name
    • Full Name
    • Customer UUID

    Supported relations:
    • customer: Returns only customer profile.
    • shipments: Returns shipments for this customer.
    • invoices: Returns invoices.
    • invoice_payments: Returns invoice payments.
    • quotations: Returns quotations.
    • pickup_orders: Returns pickup orders.
    • warehouse_receipts: Returns warehouse receipts.
    • all: Returns every related record.
    """
    service = CustomerService()
    return service.fetch(customer_identifier, relation)