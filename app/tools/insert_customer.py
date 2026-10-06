from sqlalchemy import text
from app.database.connection import SessionLocal
from langchain.tools import tool




@tool
def insert_customer(
        customer_code,
        company_name,
        email,
        contact_person=None,
        phone=None,
        address=None,
        city=None,
        state=None,
        country=None,
    ):
    """
        
    Create a new customer record in the logistics database.

    PURPOSE
    -------
    Use this tool whenever the user wants to create, register, add, onboard,
    or save a new customer/company in the logistics system.

    This tool performs a database INSERT operation and creates a permanent
    customer record.

    WHEN TO USE
    -----------
    Use this tool for requests such as:

    • Create a customer
    • Add a new customer
    • Register a customer
    • Register a company
    • Add a new company
    • Onboard a new client
    • Save customer information
    • Insert customer
    • Create customer account
    • Register business

    Examples

    User:
    Create a new customer.

    User:
    Register ABC Logistics.

    User:
    Add a customer named XYZ Industries.

    User:
    Create a company called Fast Transport.

    User:
    Add customer information.

    WHEN NOT TO USE
    ---------------
    Never use this tool if the user only wants to:

    • View customer information
    • Search customers
    • Update customer details
    • Delete a customer
    • Retrieve shipment history

    Use the appropriate Customer Lookup or Update tool instead.

    IMPORTANT WORKFLOW
    ------------------

    This tool should ONLY be called after collecting all required information.

    If required information is missing:

    1. DO NOT call the tool.
    2. Ask ONLY for the missing required fields.
    3. Never ask again for information already provided.
    4. Continue the conversation until all required fields are available.
    5. Call this tool exactly ONE time.

    Required Fields
    ---------------

    • customer_code
    • company_name
    • email

    Optional Fields
    ---------------

    • contact_person
    • phone
    • address
    • city
    • state
    • country

    VALIDATION RULES
    ----------------

    Before calling the tool:

    • Ensure customer_code is unique.
    • Ensure email appears valid.
    • Trim unnecessary whitespace.
    • Preserve user-provided values.
    • Never invent customer information.

    If the user refuses to provide optional information,
    leave those fields empty.

    CONFIRMATION
    ------------

    Before executing the database insertion,
    summarize the collected information and ask the user
    for confirmation.

    Example:

    "I have collected the following information:

    Customer Code: CUST101
    Company Name: ABC Logistics
    Email: abc@company.com

    Would you like me to create this customer?"

    Only call the tool after the user confirms.

    OUTPUT
    ------

    Returns:

    • Success status
    • Customer ID
    • Confirmation message

    If insertion fails,
    return the database error.
    """
        db = SessionLocal()

        try:

            result = db.execute(
                text("""
                    INSERT INTO customers
                    (
                        customer_code,
                        company_name,
                        contact_person,
                        email,
                        phone,
                        address,
                        city,
                        state,
                        country
                    )
                    VALUES
                    (
                        :customer_code,
                        :company_name,
                        :contact_person,
                        :email,
                        :phone,
                        :address,
                        :city,
                        :state,
                        :country
                    )
                    RETURNING customer_id;
                """),
                {
                    "customer_code": customer_code,
                    "company_name": company_name,
                    "contact_person": contact_person,
                    "email": email,
                    "phone": phone,
                    "address": address,
                    "city": city,
                    "state": state,
                    "country": country,
                },
            )

            customer_id = result.scalar()

            db.commit()

            return {
                "success": True,
                "customer_id": customer_id,
                "message": "Customer created successfully."
            }

        except Exception as e:

            db.rollback()

            return {
                "success": False,
                "error": str(e)
            }

        finally:
            db.close()