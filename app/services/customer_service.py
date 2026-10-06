from sqlalchemy import text
from app.database.connection import SessionLocal


class CustomerService:

    ####################################################################
    # Tables related with customer
    ####################################################################

    RELATIONS = {

        "shipments": {
            "table": "shipments",
            "foreign_key": "customer_id"
        },

        "invoices": {
            "table": "invoices",
            "foreign_key": "customer_id"
        },

        "invoice_payments": {
            "table": "invoice_payments",
            "foreign_key": "customer_id"
        },

        "quotations": {
            "table": "quotations",
            "foreign_key": "customer_id"
        },

        "pickup_orders": {
            "table": "pickup_orders",
            "foreign_key": "consignee_id"
        },

        "warehouse_receipts": {
            "table": "warehouse_receipts",
            "foreign_key": "customer_id"
        },

        "cargo_releases": {
            "table": "cargo_releases",
            "foreign_key": "released_to_id"
        }

    }

    ####################################################################

    def __init__(self):

        self.db = SessionLocal()

    ####################################################################

    def close(self):

        self.db.close()

    ####################################################################
    # Find Customer
    ####################################################################

    def find_customer(self, identifier: str):

        query = text("""

            SELECT *

            FROM customers

            WHERE

                customer_code = :identifier

                OR LOWER(company_name) = LOWER(:identifier)

                OR LOWER(full_name) = LOWER(:identifier)

                OR CAST(id AS TEXT) = :identifier

            LIMIT 1

        """)

        customer = self.db.execute(

            query,

            {
                "identifier": identifier
            }

        ).mappings().first()

        return customer

    ####################################################################
    # Customer Profile
    ####################################################################

    def get_customer(self, identifier):

        customer = self.find_customer(identifier)

        if customer is None:

            return {

                "success": False,

                "message": "Customer not found."

            }

        return {

            "success": True,

            "customer": dict(customer)

        }

    ####################################################################
    # Generic Relation Fetcher
    ####################################################################

    def fetch_relation(

        self,

        customer_id,

        table_name,

        foreign_key,

        customer_name=None

    ):

        if table_name == "cargo_releases":
            query = text("""
                SELECT *
                FROM cargo_releases
                WHERE released_to_id = :customer_id
                   OR (client_to_bill_type = 'customer' AND client_to_bill = CAST(:customer_id AS TEXT))
                   OR (LOWER(released_to_name) = LOWER(:customer_name) AND :customer_name != '')
            """)
            rows = self.db.execute(
                query,
                {
                    "customer_id": customer_id,
                    "customer_name": customer_name or ""
                }
            ).mappings().all()
            return [dict(row) for row in rows]

        query = text(f"""

            SELECT *

            FROM {table_name}

            WHERE {foreign_key} = :customer_id

        """)

        rows = self.db.execute(

            query,

            {

                "customer_id": customer_id

            }

        ).mappings().all()

        return [dict(row) for row in rows]

    ####################################################################
    # Fetch One Relation
    ####################################################################

    def get_relation(

        self,

        customer_identifier,

        relation

    ):

        customer = self.find_customer(customer_identifier)

        if customer is None:

            return {

                "success": False,

                "message": "Customer not found."

            }

        customer = dict(customer)

        if relation not in self.RELATIONS:

            return {

                "success": False,

                "message": f"Unknown relation '{relation}'."

            }

        config = self.RELATIONS[relation]

        records = self.fetch_relation(

            customer["id"],

            config["table"],

            config["foreign_key"],

            customer_name=customer.get("full_name") or customer.get("company_name")

        )

        return {

            "success": True,

            "customer": customer,

            relation: records

        }

    ####################################################################
    # Fetch Everything
    ####################################################################

    def get_all(self, customer_identifier):

        customer = self.find_customer(customer_identifier)

        if customer is None:

            return {

                "success": False,

                "message": "Customer not found."

            }

        customer = dict(customer)

        result = {

            "success": True,

            "customer": customer

        }

        for relation_name, config in self.RELATIONS.items():

            result[relation_name] = self.fetch_relation(

                customer["id"],

                config["table"],

                config["foreign_key"],

                customer_name=customer.get("full_name") or customer.get("company_name")

            )

        return result

    ####################################################################
    # Public API
    ####################################################################

    def fetch(

        self,

        customer_identifier,

        relation="customer"

    ):

        try:

            if relation == "customer":

                return self.get_customer(customer_identifier)

            elif relation == "all":

                return self.get_all(customer_identifier)

            else:

                return self.get_relation(

                    customer_identifier,

                    relation

                )

        finally:

            self.close()