from langchain.tools import tool
from app.services.driver_service import DriverService


@tool
def get_driver_details(driver_identifier: str, relation: str = "driver"):
    """
    Retrieve comprehensive driver/employee information from the logistics database.

    PURPOSE:
    This tool retrieves complete details about a logistics driver or employee,
    including personal information, contact details, role, employment status,
    and associated orders.

    Supported relations:
    - driver: Returns driver/employee profile information.
    - all: Returns driver details plus all associated records.
    - pickup_orders: Returns pickup orders linked to this employee.
    - quotations: Returns quotations linked to this employee.
    - cargo_releases: Returns cargo release records linked to this employee.
    """
    service = DriverService()
    return service.fetch(driver_identifier, relation)