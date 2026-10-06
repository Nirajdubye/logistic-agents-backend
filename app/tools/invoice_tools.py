from langchain.tools import tool
from app.services.invoice_service import InvoiceService


@tool
def get_invoice_details(invoice_identifier: str, relation: str = "invoice"):
    """
    Retrieve comprehensive Invoice information from the logistics database.

    PURPOSE:
    This tool retrieves complete information about a logistics billing invoice,
    including total amounts, balance due, payment status, customer information,
    line items (`invoice_items`), payment history, and billing notes.

    WHEN TO USE:
    Use this tool whenever the user requests information about an invoice,
    billing statement, payment status, balance due, or invoice charges.

    Supported relations:
    - invoice: Returns invoice summary, total amount, balance due, and line items.
    - all: Returns invoice record plus all associated relation tables.
    - invoice_items: Returns detailed line items for this invoice.
    - invoice_payments: Returns payment records for this invoice.
    - invoice_status_history: Returns historical status audit logs.
    """
    service = InvoiceService()
    return service.fetch(invoice_identifier, relation)
