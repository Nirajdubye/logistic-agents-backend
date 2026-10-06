from langchain_core.tools import tool
from sqlalchemy import text
from app.database.connection import SessionLocal
from app.services.warehouse_receipt_service import WarehouseReceiptService
@tool
def get_warehouse_receipt_details(receipt_identifier: str, relation: str = "warehouse_receipt"):
    """
    Retrieve comprehensive Warehouse Receipt information from the logistics database.

    PURPOSE
    -------
    This tool retrieves complete information about a warehouse receipt,
    including receipt details, customer information, warehouse information,
    carrier details, shipment information, insurance information,
    financial details, receipt status, and associated metadata.

    This tool should always be used whenever the user wants to
    retrieve, search, track, or inspect warehouse receipt information.

    --------------------------------------------------------------------
    WHEN TO USE
    --------------------------------------------------------------------

    Use this tool whenever the user's request is related to:

    • Warehouse Receipt
    • Receipt Details
    • Warehouse Entry
    • Goods Receipt
    • Receipt Status
    • Receipt Information
    • Warehouse Storage
    • Inventory Receipt
    • Purchase Tracking
    • Stored Cargo
    • Receipt Document

    --------------------------------------------------------------------
    USER REQUEST EXAMPLES
    --------------------------------------------------------------------

    General Lookup

    • Show warehouse receipt WR0001
    • Find receipt WR10025
    • Display warehouse receipt
    • Get warehouse receipt details
    • Search receipt
    • Warehouse receipt information

    Tracking

    • Track warehouse receipt WR0001
    • Show receipt status
    • Current warehouse receipt status
    • Is my cargo received?
    • Warehouse storage status

    Customer

    • Show warehouse receipt for customer ABC Logistics
    • Customer warehouse receipt
    • Warehouse receipt of XYZ Industries

    Warehouse

    • Which warehouse contains receipt WR1001?
    • Warehouse information
    • Storage location

    Insurance

    • Is this shipment insured?
    • Insurance information
    • Insurance number
    • Insured value

    Financial

    • Warehouse charges
    • Receipt value
    • Total cargo value
    • Receipt charges

    Cargo

    • Cargo description
    • Number of pieces
    • Weight
    • Dimensions
    • Serial Number
    • Model Number

    --------------------------------------------------------------------
    INPUT
    --------------------------------------------------------------------

    receipt_identifier (str)

    Accepts any of the following:

    • Receipt Number

      Example

      WR0001
      WR10025

    • Receipt Document Number

      Example

      DOC-2026-001

    • Purchase Tracking Number

      Example

      PT-45896

    --------------------------------------------------------------------
    OUTPUT
    --------------------------------------------------------------------

    Returns warehouse receipt information including:

    Receipt Information

    • Receipt Number
    • Receipt Document Number
    • Receipt Status
    • Received Date

    Customer Information

    • Customer Name

    Warehouse Information

    • Warehouse ID

    Cargo Information

    • Description
    • Pieces
    • Total Weight
    • Dimensions
    • Part Number
    • Model Number
    • Serial Number

    Shipping Information

    • Carrier Name
    • Driver Name
    • Purchase Tracking Number

    Supplier Information

    • Supplier Name

    Insurance Information

    • Is Insured
    • Insurance Number
    • Insured Value

    Financial Information

    • Cargo Value
    • Applicable Charges

    Additional Information

    • Agent Name
    • Associated Entity
    • Notes

    --------------------------------------------------------------------
    RECEIPT STATUS MAY INCLUDE
    --------------------------------------------------------------------

    • Pending
    • Received
    • Processing
    • Stored
    • Released
    • Completed
    • Cancelled

    --------------------------------------------------------------------
    IF RECEIPT IS NOT FOUND
    --------------------------------------------------------------------

    Return a failure response indicating that the warehouse receipt
    does not exist in the logistics database.

    --------------------------------------------------------------------
    IMPORTANT
    --------------------------------------------------------------------

    This tool is READ ONLY.

    Never use this tool to:

    • Create a warehouse receipt
    • Update warehouse receipt
    • Delete warehouse receipt
    • Change receipt status
    • Release cargo
    • Modify insurance information
    • Edit warehouse data

    Those operations should be handled by dedicated warehouse
    management tools.

    --------------------------------------------------------------------
    TOOL SELECTION GUIDELINES
    --------------------------------------------------------------------

    ALWAYS use this tool if the user asks about:

    ✓ Warehouse Receipt
    ✓ Receipt Number
    ✓ Receipt Status
    ✓ Receipt Details
    ✓ Goods Received
    ✓ Warehouse Storage
    ✓ Cargo Receipt
    ✓ Warehouse Entry
    ✓ Receipt Document
    ✓ Purchase Tracking

    DO NOT use this tool if the user is asking about:

    ✗ Shipment Tracking
    ✗ Customer Profile
    ✗ Invoice Details
    ✗ Driver Information
    ✗ Vehicle Information

    Use the corresponding Shipment, Customer, Invoice,
    Driver, or Vehicle tool instead.

    --------------------------------------------------------------------
    TOOL PRIORITY
    --------------------------------------------------------------------

    If the user's primary intent is to retrieve information about
    a warehouse receipt, ALWAYS prefer this tool over Shipment
    or Customer tools.

    If the user provides a Receipt Number,
    Receipt Document Number, or Purchase Tracking Number,
    this tool should be selected immediately.
    """

    service = WarehouseReceiptService()
    return service.fetch(
        receipt_identifier,
        relation
    )