from langchain.tools import tool
from app.services.quotation_service import QuotationService


@tool
def get_quotation_details(quote_identifier: str, relation: str = "quotation"):
    """
    Retrieve detailed Quotation information from the logistics database.

    PURPOSE:
    This tool retrieves complete information about a logistics quote/quotation,
    including quotation status, dates, customer details, route, transport mode,
    commodities (`quotation_commodities`), charges (`quotation_charges`), and notes.

    WHEN TO USE:
    Use this tool whenever the user requests information about a quotation,
    quote status, pricing proposal, quote history, or quote commodities.

    Supported relations:
    - quotation: Returns quotation details, commodities, and charges.
    - all: Returns quotation record plus all associated relation tables.
    - quotation_commodities: Returns commodity line items.
    - quotation_charges: Returns quotation charge items.
    - quotation_notes: Returns quotation notes.
    - quotation_events: Returns audit event logs.
    - quotation_attachments: Returns quotation attachments.
    """
    service = QuotationService()
    return service.fetch(quote_identifier, relation)
