from sqlalchemy import text
from app.database.connection import SessionLocal


class QuotationService:

    ####################################################################
    # Tables related with Quotation
    ####################################################################

    RELATIONS = {
        "quotation_commodities": {
            "table": "quotation_commodities",
            "foreign_key": "quotation_id"
        },
        "quotation_charges": {
            "table": "quotation_charges",
            "foreign_key": "quotation_id"
        },
        "quotation_notes": {
            "table": "quotation_notes",
            "foreign_key": "quotation_id"
        },
        "quotation_events": {
            "table": "quotation_events",
            "foreign_key": "quotation_id"
        },
        "quotation_attachments": {
            "table": "quotation_attachments",
            "foreign_key": "quotation_id"
        }
    }

    ####################################################################

    def __init__(self):
        self.db = SessionLocal()

    ####################################################################

    def close(self):
        self.db.close()

    ####################################################################
    # Find Quotation Record
    ####################################################################

    def find_quotation(self, identifier: str):
        query = text("""
            SELECT *
            FROM quotations
            WHERE
                LOWER(quote_no) = LOWER(:identifier)
                OR CAST(id AS TEXT) = :identifier
            LIMIT 1
        """)

        quotation = self.db.execute(
            query,
            {"identifier": identifier.strip()}
        ).mappings().first()

        return quotation

    ####################################################################
    # Comprehensive Quotation Details
    ####################################################################

    def get_quotation_details(self, identifier: str):
        quotation = self.find_quotation(identifier)

        if quotation is None:
            return {
                "success": False,
                "message": f"Quotation '{identifier}' not found."
            }

        q = dict(quotation)
        quotation_id = q["id"]

        # Fetch commodities
        commodities_query = text("SELECT * FROM quotation_commodities WHERE quotation_id = :qid ORDER BY created_at ASC")
        commodities = self.db.execute(commodities_query, {"qid": quotation_id}).mappings().all()
        commodity_list = [dict(c) for c in commodities]

        # Fetch charges
        charges_query = text("SELECT * FROM quotation_charges WHERE quotation_id = :qid ORDER BY created_at ASC")
        charges = self.db.execute(charges_query, {"qid": quotation_id}).mappings().all()
        charge_list = [dict(c) for c in charges]

        return {
            "success": True,
            "quote_no": q["quote_no"],
            "status": q["status"],
            "date": str(q["date"]) if q.get("date") else None,
            "exp_date": str(q["exp_date"]) if q.get("exp_date") else None,
            "customer_name": q.get("customer_name"),
            "employee_name": q.get("employee_name"),
            "salesperson": q.get("salesperson"),
            "mode_of_transportation": q.get("mode_of_transportation"),
            "route": q.get("route"),
            "port_of_loading": q.get("port_of_loading"),
            "port_of_unloading": q.get("port_of_unloading"),
            "incoterms": q.get("incoterms"),
            "payment_terms": q.get("payment_terms"),
            "description_of_goods": q.get("description_of_goods"),
            "commodities": commodity_list,
            "charges": charge_list,
            "quotation": q
        }

    ####################################################################
    # Generic Relation Fetcher
    ####################################################################

    def fetch_relation(self, quotation_id, table_name, foreign_key):
        query = text(f"""
            SELECT *
            FROM {table_name}
            WHERE {foreign_key} = :quotation_id
        """)
        rows = self.db.execute(query, {"quotation_id": quotation_id}).mappings().all()
        return [dict(row) for row in rows]

    ####################################################################
    # Fetch One Relation
    ####################################################################

    def get_relation(self, identifier, relation):
        quotation = self.find_quotation(identifier)
        if quotation is None:
            return {
                "success": False,
                "message": f"Quotation '{identifier}' not found."
            }

        q_dict = dict(quotation)
        if relation not in self.RELATIONS:
            return {
                "success": False,
                "message": f"Unknown relation '{relation}'."
            }

        config = self.RELATIONS[relation]
        records = self.fetch_relation(
            q_dict["id"],
            config["table"],
            config["foreign_key"]
        )

        return {
            "success": True,
            "quotation": q_dict,
            relation: records
        }

    ####################################################################
    # Fetch All
    ####################################################################

    def get_all(self, identifier):
        details = self.get_quotation_details(identifier)
        if not details.get("success"):
            return details

        quotation = self.find_quotation(identifier)
        if quotation is None:
            return details

        result = dict(details)
        for relation_name, config in self.RELATIONS.items():
            result[relation_name] = self.fetch_relation(
                quotation["id"],
                config["table"],
                config["foreign_key"]
            )

        return result

    ####################################################################
    # Unified Public Entry Point
    ####################################################################

    def fetch(self, identifier, relation="quotation"):
        try:
            if relation in ("quotation", "details", "quote"):
                return self.get_quotation_details(identifier)
            elif relation == "all":
                return self.get_all(identifier)
            else:
                return self.get_relation(identifier, relation)
        finally:
            self.close()
