from sqlalchemy import text
from app.database.connection import SessionLocal


class WarehouseReceiptService:

    ####################################################################
    # Tables related with Warehouse Receipt
    ####################################################################

    RELATIONS = {

        "warehouse_receipt_packages": {
            "table": "warehouse_receipt_packages",
            "foreign_key": "warehouse_receipt_id"
        },

        "warehouse_receipt_package_attachments": {
            "table": "warehouse_receipt_package_attachments",
            "foreign_key": "warehouse_receipt_id"
        },

        "warehouse_receipt_items": {
            "table": "warehouse_receipt_items",
            "foreign_key": "warehouse_receipt_id"
        },

        "warehouse_receipt_attachments": {
            "table": "warehouse_receipt_attachments",
            "foreign_key": "warehouse_receipt_id"
        },

        "shipment_packages": {
            "table": "shipment_packages",
            "foreign_key": "warehouse_receipt_id"
        },

        "quotation_commodities": {
            "table": "quotation_commodities",
            "foreign_key": "warehouse_receipt_id"
        },

        "cargo_releases": {
            "table": "cargo_releases",
            "foreign_key": "warehouse_receipt_id"
        },

        "cargo_release_commodities": {
            "table": "cargo_release_commodities",
            "foreign_key": "warehouse_receipt_id"
        }

    }

    ####################################################################

    def __init__(self):

        self.db = SessionLocal()

    ####################################################################

    def close(self):

        self.db.close()

    ####################################################################
    # Find Warehouse Receipt
    ####################################################################

    def find_receipt(self, identifier: str):

        query = text("""

            SELECT *

            FROM warehouse_receipts

            WHERE

                LOWER(receipt_no) = LOWER(:identifier)

                OR LOWER(receipt_document_no) = LOWER(:identifier)

                OR LOWER(purchase_tracking_no) = LOWER(:identifier)

                OR CAST(id AS TEXT) = :identifier

            LIMIT 1

        """)

        receipt = self.db.execute(

            query,

            {
                "identifier": identifier.strip()
            }

        ).mappings().first()

        return receipt

    ####################################################################
    # Warehouse Receipt Profile
    ####################################################################

    def get_receipt(self, identifier):

        receipt = self.find_receipt(identifier)

        if receipt is None:

            return {

                "success": False,

                "message": "Warehouse Receipt not found."

            }

        rec_dict = dict(receipt)

        # Fetch warehouse receipt packages if available
        pkg_query = text("""
            SELECT *
            FROM warehouse_receipt_packages
            WHERE warehouse_receipt_id = :wrid
            ORDER BY line_no ASC
        """)
        packages = self.db.execute(pkg_query, {"wrid": rec_dict["id"]}).mappings().all()
        package_list = [dict(p) for p in packages]

        return {

            "success": True,

            "warehouse_receipt": rec_dict,

            "packages": package_list

        }

    ####################################################################
    # Generic Relation Fetcher
    ####################################################################

    def fetch_relation(

        self,

        receipt_id,

        table_name,

        foreign_key

    ):

        query = text(f"""

            SELECT *

            FROM {table_name}

            WHERE {foreign_key} = :receipt_id

        """)

        rows = self.db.execute(

            query,

            {

                "receipt_id": receipt_id

            }

        ).mappings().all()

        return [dict(row) for row in rows]

    ####################################################################
    # Fetch One Relation
    ####################################################################

    def get_relation(

        self,

        receipt_identifier,

        relation

    ):

        receipt = self.find_receipt(receipt_identifier)

        if receipt is None:

            return {

                "success": False,

                "message": "Warehouse Receipt not found."

            }

        receipt = dict(receipt)

        if relation not in self.RELATIONS:

            return {

                "success": False,

                "message": f"Unknown relation '{relation}'."

            }

        config = self.RELATIONS[relation]

        records = self.fetch_relation(

            receipt["id"],

            config["table"],

            config["foreign_key"]

        )

        return {

            "success": True,

            "warehouse_receipt": receipt,

            relation: records

        }

    ####################################################################
    # Fetch Everything
    ####################################################################

    def get_all(self, receipt_identifier):

        receipt = self.find_receipt(receipt_identifier)

        if receipt is None:

            return {

                "success": False,

                "message": "Warehouse Receipt not found."

            }

        receipt = dict(receipt)

        result = {

            "success": True,

            "warehouse_receipt": receipt

        }

        for relation_name, config in self.RELATIONS.items():

            result[relation_name] = self.fetch_relation(

                receipt["id"],

                config["table"],

                config["foreign_key"]

            )

        return result

    ####################################################################
    # Public API
    ####################################################################

    def fetch(

        self,

        receipt_identifier,

        relation="warehouse_receipt"

    ):

        try:

            if relation == "warehouse_receipt":

                return self.get_receipt(receipt_identifier)

            elif relation == "all":

                return self.get_all(receipt_identifier)

            else:

                return self.get_relation(

                    receipt_identifier,

                    relation

                )

        finally:

            self.close()