from sqlalchemy import text
from app.database.connection import SessionLocal


class ShipmentService:

    ####################################################################
    # Tables related with shipment
    ####################################################################

    RELATIONS = {

        "shipment_addresses": {
            "table": "shipment_addresses",
            "foreign_key": "shipment_id"
        },

        "shipment_packages": {
            "table": "shipment_packages",
            "foreign_key": "shipment_id"
        },

        "invoices": {
            "table": "invoices",
            "foreign_key": "shipment_id"
        },

        "cargo_releases": {
            "table": "cargo_releases",
            "foreign_key": "shipment_id"
        },

        "shipment_status_history": {
            "table": "shipment_status_history",
            "foreign_key": "shipment_id"
        }

    }

    ####################################################################

    def __init__(self):
        self.db = SessionLocal()

    ####################################################################

    def close(self):
        self.db.close()

    ####################################################################
    # Find Shipment Record
    ####################################################################

    def find_shipment(self, identifier: str):
        query = text("""
            SELECT *
            FROM shipments
            WHERE
                LOWER(shipment_no) = LOWER(:identifier)
                OR LOWER(tracking_no) = LOWER(:identifier)
                OR CAST(id AS TEXT) = :identifier
            LIMIT 1
        """)

        shipment = self.db.execute(
            query,
            {"identifier": identifier.strip()}
        ).mappings().first()

        return shipment

    ####################################################################
    # Comprehensive Shipment Details
    ####################################################################

    def get_shipment_details(self, identifier: str):
        query = text("""
            SELECT
                s.id,
                s.shipment_no,
                s.tracking_no,
                s.shipment_name,
                s.shipment_mode,
                s.status,
                s.booking_stage,
                s.delivery_priority,
                s.is_insured,
                s.pickup_date,
                s.preferred_delivery_date,
                s.current_step,
                s.base_shipping_charge,
                s.weight_charge,
                s.insurance_charge,
                s.total_estimated_cost,
                s.total_volume,
                s.total_pieces,
                s.total_parcels,
                s.total_weight,
                s.total_value,
                s.insurance_number,
                s.insured_value,
                s.delivery_priority_charge,
                s.progress_percent,
                s.notes,
                s.created_at,
                s.updated_at,

                c.customer_code,
                c.company_name AS customer_company,
                c.full_name AS customer_name,
                c.email AS customer_email,
                c.phone_number AS customer_phone,

                a.agent_code,
                a.company_name AS agent_company,
                a.full_name AS agent_name,

                addr_pickup.company_name AS origin_company,
                addr_pickup.contact_name AS origin_contact,
                addr_pickup.phone_number AS origin_phone,
                addr_pickup.address_line_1 AS origin_address_line_1,
                addr_pickup.address_line_2 AS origin_address_line_2,
                addr_pickup.city AS origin_city,
                addr_pickup.state_province AS origin_state,
                addr_pickup.country AS origin_country,
                addr_pickup.zip_code AS origin_zip,

                addr_delivery.company_name AS destination_company,
                addr_delivery.contact_name AS destination_contact,
                addr_delivery.phone_number AS destination_phone,
                addr_delivery.address_line_1 AS destination_address_line_1,
                addr_delivery.address_line_2 AS destination_address_line_2,
                addr_delivery.city AS destination_city,
                addr_delivery.state_province AS destination_state,
                addr_delivery.country AS destination_country,
                addr_delivery.zip_code AS destination_zip

            FROM shipments s

            LEFT JOIN customers c
                ON s.customer_id = c.id

            LEFT JOIN agents a
                ON s.agent_id = a.id

            LEFT JOIN shipment_addresses addr_pickup
                ON s.id = addr_pickup.shipment_id AND addr_pickup.address_type = 'pickup'

            LEFT JOIN shipment_addresses addr_delivery
                ON s.id = addr_delivery.shipment_id AND addr_delivery.address_type = 'delivery'

            WHERE
                LOWER(s.shipment_no) = LOWER(:identifier)
                OR LOWER(s.tracking_no) = LOWER(:identifier)
                OR CAST(s.id AS TEXT) = :identifier
        """)

        row = self.db.execute(
            query,
            {"identifier": identifier.strip()}
        ).mappings().first()

        if row is None:
            return {
                "success": False,
                "message": f"Shipment '{identifier}' not found."
            }

        origin_parts = [
            row["origin_address_line_1"],
            row["origin_city"],
            row["origin_state"],
            row["origin_country"]
        ]
        origin_str = ", ".join([p for p in origin_parts if p])

        dest_parts = [
            row["destination_address_line_1"],
            row["destination_city"],
            row["destination_state"],
            row["destination_country"]
        ]
        destination_str = ", ".join([p for p in dest_parts if p])

        customer_str = (
            row["customer_company"]
            or row["customer_name"]
            or row["customer_code"]
            or "N/A"
        )

        weight_val = float(row["total_weight"]) if row["total_weight"] is not None else 0.0
        expected_delivery_str = (
            str(row["preferred_delivery_date"])
            if row["preferred_delivery_date"]
            else (str(row["pickup_date"]) if row["pickup_date"] else None)
        )

        pkg_query = text("""
            SELECT line_no, package_name, parcel_number, quantity, weight_kg, declared_value, description
            FROM shipment_packages
            WHERE shipment_id = :sid
            ORDER BY line_no ASC
        """)
        pkgs = self.db.execute(pkg_query, {"sid": row["id"]}).mappings().all()
        packages_list = [
            {
                "line_no": p["line_no"],
                "package_name": p["package_name"],
                "parcel_number": p["parcel_number"],
                "quantity": p["quantity"],
                "weight_kg": float(p["weight_kg"]) if p["weight_kg"] is not None else 0.0,
                "declared_value": float(p["declared_value"]) if p["declared_value"] is not None else 0.0,
                "description": p["description"]
            }
            for p in pkgs
        ]

        current_location_str = (
            destination_str
            if str(row["status"]).lower() == "delivered"
            else (origin_str or "In Transit")
        )

        return {
            "success": True,
            "shipment_id": row["shipment_no"],
            "tracking_number": row["tracking_no"],
            "shipment_no": row["shipment_no"],
            "shipment_name": row["shipment_name"],
            "customer": customer_str,
            "customer_details": {
                "code": row["customer_code"],
                "company": row["customer_company"],
                "name": row["customer_name"],
                "email": row["customer_email"],
                "phone": row["customer_phone"],
            },
            "status": str(row["status"]),
            "shipment_mode": str(row["shipment_mode"]),
            "booking_stage": str(row["booking_stage"]),
            "delivery_priority": str(row["delivery_priority"]),
            "origin": origin_str or "N/A",
            "destination": destination_str or "N/A",
            "current_location": current_location_str,
            "weight": weight_val,
            "total_pieces": row["total_pieces"],
            "total_parcels": row["total_parcels"],
            "total_estimated_cost": float(row["total_estimated_cost"]) if row["total_estimated_cost"] is not None else 0.0,
            "pickup_date": str(row["pickup_date"]) if row["pickup_date"] else None,
            "expected_delivery": expected_delivery_str,
            "progress_percent": row["progress_percent"],
            "packages": packages_list,
            "notes": row["notes"]
        }

    ####################################################################
    # Generic Relation Fetcher
    ####################################################################

    def fetch_relation(self, shipment_id, table_name, foreign_key):
        query = text(f"""
            SELECT *
            FROM {table_name}
            WHERE {foreign_key} = :shipment_id
        """)
        rows = self.db.execute(query, {"shipment_id": shipment_id}).mappings().all()
        return [dict(row) for row in rows]

    ####################################################################
    # Fetch One Relation
    ####################################################################

    def get_relation(self, identifier, relation):
        shipment = self.find_shipment(identifier)
        if shipment is None:
            return {
                "success": False,
                "message": f"Shipment '{identifier}' not found."
            }

        shipment_dict = dict(shipment)
        if relation not in self.RELATIONS:
            return {
                "success": False,
                "message": f"Unknown relation '{relation}'."
            }

        config = self.RELATIONS[relation]
        records = self.fetch_relation(
            shipment_dict["id"],
            config["table"],
            config["foreign_key"]
        )

        return {
            "success": True,
            "shipment": shipment_dict,
            relation: records
        }

    ####################################################################
    # Fetch Everything Related to Shipment
    ####################################################################

    def get_all(self, identifier):
        details = self.get_shipment_details(identifier)
        if not details.get("success"):
            return details

        shipment = self.find_shipment(identifier)
        if shipment is None:
            return details

        result = dict(details)
        for relation_name, config in self.RELATIONS.items():
            result[relation_name] = self.fetch_relation(
                shipment["id"],
                config["table"],
                config["foreign_key"]
            )

        return result

    ####################################################################
    # Unified Public Entry Point
    ####################################################################

    def fetch(self, identifier, relation="shipment"):
        try:
            if relation in ("shipment", "status", "details"):
                return self.get_shipment_details(identifier)
            elif relation == "all":
                return self.get_all(identifier)
            else:
                return self.get_relation(identifier, relation)
        finally:
            self.close()
