from langchain.tools import tool
from app.services.cargo_release_service import CargoReleaseService


@tool
def get_cargo_release_details(release_identifier: str, relation: str = "cargo_release"):
    """
    Retrieve detailed Cargo Release information from the logistics database.

    PURPOSE:
    This tool retrieves complete information about a cargo release record,
    including release status, carrier details, driver details, tracking numbers,
    purchase order numbers, released-to recipient information, and line commodities.

    WHEN TO USE:
    Use this tool whenever the user requests information about a cargo release,
    goods release, release status, or cargo delivery authorization.

    Supported relations:
    - cargo_release: Returns cargo release details and line commodities.
    - all: Returns cargo release record plus all associated relation tables.
    - cargo_release_commodities: Returns commodity line items for this cargo release.
    """
    service = CargoReleaseService()
    return service.fetch(release_identifier, relation)
