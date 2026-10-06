from langchain.tools import tool
from app.services.shipment_service import ShipmentService


@tool
def get_shipment_status(shipment_id: str, relation: str = "shipment"):
    """
    Retrieve detailed shipment information from the logistics database.

    PURPOSE:
    This tool retrieves comprehensive information about a shipment,
    including its current status, customer details, origin,
    destination, assigned driver, assigned vehicle,
    delivery information, shipment progress, and package details.

    WHEN TO USE:
    Use this tool whenever the user requests information about a shipment,
    package, delivery, order transportation, shipment tracking,
    shipment progress, shipment status, shipment location,
    or shipment history.

    Supported relations:
    - shipment: Returns detailed shipment information, addresses, customer details, and packages.
    - all: Returns shipment details plus all associated raw relation tables.
    - shipment_addresses: Returns origin and destination address records.
    - shipment_packages: Returns package line items.
    - invoices: Returns billing invoices for this shipment.
    - cargo_releases: Returns cargo release records for this shipment.
    - shipment_status_history: Returns historical tracking events.
    """
    service = ShipmentService()
    return service.fetch(shipment_id, relation)