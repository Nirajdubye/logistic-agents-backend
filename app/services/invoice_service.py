from sqlalchemy import text
from app.database.connection import SessionLocal


class InvoiceService:

    ####################################################################
    # Tables related with Invoice
    ####################################################################

    RELATIONS = {
        "invoice_items": {
            "table": "invoice_items",
            "foreign_key": "invoice_id"
        },
        "invoice_payments": {
            "table": "invoice_payments",
            "foreign_key": "invoice_id"
        },
        "invoice_status_history": {
            "table": "invoice_status_history",
            "foreign_key": "invoice_id"
        }
    }

    ####################################################################

    def __init__(self):
        self.db = SessionLocal()

    ####################################################################

    def close(self):
        self.db.close()

    ####################################################################
    # Find Invoice Record
    ####################################################################

    def find_invoice(self, identifier: str):
        query = text("""
            SELECT *
            FROM invoices
            WHERE
                LOWER(invoice_no) = LOWER(:identifier)
                OR CAST(id AS TEXT) = :identifier
            LIMIT 1
        """)

        invoice = self.db.execute(
            query,
            {"identifier": identifier.strip()}
        ).mappings().first()

        return invoice

    ####################################################################
    # Comprehensive Invoice Details
    ####################################################################

    def get_invoice_details(self, identifier: str):
        invoice = self.find_invoice(identifier)

        if invoice is None:
            return {
                "success": False,
                "message": f"Invoice '{identifier}' not found."
            }

        inv = dict(invoice)
        invoice_id = inv["id"]

        # Fetch customer company/name if available
        customer_name = "N/A"
        if inv.get("customer_id"):
            cust_query = text("SELECT company_name, full_name, customer_code FROM customers WHERE id = :cid")
            cust_row = self.db.execute(cust_query, {"cid": inv["customer_id"]}).mappings().first()
            if cust_row:
                customer_name = cust_row["company_name"] or cust_row["full_name"] or cust_row["customer_code"]

        # Fetch invoice items
        items_query = text("SELECT * FROM invoice_items WHERE invoice_id = :iid ORDER BY sort_order ASC")
        items_rows = self.db.execute(items_query, {"iid": invoice_id}).mappings().all()
        items_list = [dict(item) for item in items_rows]

        # Fetch payment history
        payments_query = text("SELECT * FROM invoice_payments WHERE invoice_id = :iid ORDER BY payment_date DESC")
        payments_rows = self.db.execute(payments_query, {"iid": invoice_id}).mappings().all()
        payments_list = [dict(pmt) for pmt in payments_rows]

        return {
            "success": True,
            "invoice_no": inv["invoice_no"],
            "status": inv["status"],
            "payment_status": inv["payment_status"],
            "invoice_date": str(inv["invoice_date"]) if inv.get("invoice_date") else None,
            "due_date": str(inv["due_date"]) if inv.get("due_date") else None,
            "customer": customer_name,
            "subtotal": float(inv["subtotal"]) if inv.get("subtotal") is not None else 0.0,
            "tax_amount": float(inv["tax_amount"]) if inv.get("tax_amount") is not None else 0.0,
            "discount_amount": float(inv["discount_amount"]) if inv.get("discount_amount") is not None else 0.0,
            "total_amount": float(inv["total_amount"]) if inv.get("total_amount") is not None else 0.0,
            "amount_paid": float(inv["amount_paid"]) if inv.get("amount_paid") is not None else 0.0,
            "balance_due": float(inv["balance_due"]) if inv.get("balance_due") is not None else 0.0,
            "items": items_list,
            "payments": payments_list,
            "invoice": inv
        }

    ####################################################################
    # Generic Relation Fetcher
    ####################################################################

    def fetch_relation(self, invoice_id, table_name, foreign_key):
        query = text(f"""
            SELECT *
            FROM {table_name}
            WHERE {foreign_key} = :invoice_id
        """)
        rows = self.db.execute(query, {"invoice_id": invoice_id}).mappings().all()
        return [dict(row) for row in rows]

    ####################################################################
    # Fetch One Relation
    ####################################################################

    def get_relation(self, identifier, relation):
        invoice = self.find_invoice(identifier)
        if invoice is None:
            return {
                "success": False,
                "message": f"Invoice '{identifier}' not found."
            }

        inv_dict = dict(invoice)
        if relation not in self.RELATIONS:
            return {
                "success": False,
                "message": f"Unknown relation '{relation}'."
            }

        config = self.RELATIONS[relation]
        records = self.fetch_relation(
            inv_dict["id"],
            config["table"],
            config["foreign_key"]
        )

        return {
            "success": True,
            "invoice": inv_dict,
            relation: records
        }

    ####################################################################
    # Fetch All
    ####################################################################

    def get_all(self, identifier):
        details = self.get_invoice_details(identifier)
        if not details.get("success"):
            return details

        invoice = self.find_invoice(identifier)
        if invoice is None:
            return details

        result = dict(details)
        for relation_name, config in self.RELATIONS.items():
            result[relation_name] = self.fetch_relation(
                invoice["id"],
                config["table"],
                config["foreign_key"]
            )

        return result

    ####################################################################
    # Unified Public Entry Point
    ####################################################################

    def fetch(self, identifier, relation="invoice"):
        try:
            if relation in ("invoice", "details", "summary"):
                return self.get_invoice_details(identifier)
            elif relation == "all":
                return self.get_all(identifier)
            else:
                return self.get_relation(identifier, relation)
        finally:
            self.close()
