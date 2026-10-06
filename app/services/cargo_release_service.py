from sqlalchemy import text
from app.database.connection import SessionLocal


class CargoReleaseService:

    ####################################################################
    # Tables related with Cargo Release
    ####################################################################

    RELATIONS = {
        "cargo_release_commodities": {
            "table": "cargo_release_commodities",
            "foreign_key": "cargo_release_id"
        }
    }

    ####################################################################

    def __init__(self):
        self.db = SessionLocal()

    ####################################################################

    def close(self):
        self.db.close()

    ####################################################################
    # Find Cargo Release Record
    ####################################################################

    def find_release(self, identifier: str):
        query = text("""
            SELECT *
            FROM cargo_releases
            WHERE
                LOWER(release_number) = LOWER(:identifier)
                OR LOWER(tracking_number) = LOWER(:identifier)
                OR LOWER(pro_number) = LOWER(:identifier)
                OR LOWER(purchase_order_number) = LOWER(:identifier)
                OR CAST(id AS TEXT) = :identifier
            LIMIT 1
        """)

        release = self.db.execute(
            query,
            {"identifier": identifier.strip()}
        ).mappings().first()

        return release

    ####################################################################
    # Cargo Release Details
    ####################################################################

    def get_release_details(self, identifier: str):
        release = self.find_release(identifier)

        if release is None:
            return {
                "success": False,
                "message": f"Cargo Release '{identifier}' not found."
            }

        rel = dict(release)
        release_id = rel["id"]

        # Fetch commodities
        commodities_query = text("""
            SELECT *
            FROM cargo_release_commodities
            WHERE cargo_release_id = :rid
            ORDER BY created_at ASC
        """)
        commodities = self.db.execute(
            commodities_query,
            {"rid": release_id}
        ).mappings().all()

        commodity_list = [dict(c) for c in commodities]

        return {
            "success": True,
            "release_number": rel["release_number"],
            "status": rel["status"],
            "creation_date": str(rel["creation_date"]) if rel.get("creation_date") else None,
            "release_date": str(rel["release_date"]) if rel.get("release_date") else None,
            "carrier_name": rel.get("carrier_name"),
            "driver_name": rel.get("driver_name"),
            "driver_license_number": rel.get("driver_license_number"),
            "pro_number": rel.get("pro_number"),
            "tracking_number": rel.get("tracking_number"),
            "purchase_order_number": rel.get("purchase_order_number"),
            "released_to_name": rel.get("released_to_name"),
            "client_to_bill": rel.get("client_to_bill"),
            "notes": rel.get("notes"),
            "commodities": commodity_list,
            "cargo_release": rel
        }

    ####################################################################
    # Generic Relation Fetcher
    ####################################################################

    def fetch_relation(self, release_id, table_name, foreign_key):
        query = text(f"""
            SELECT *
            FROM {table_name}
            WHERE {foreign_key} = :release_id
        """)
        rows = self.db.execute(query, {"release_id": release_id}).mappings().all()
        return [dict(row) for row in rows]

    ####################################################################
    # Fetch One Relation
    ####################################################################

    def get_relation(self, identifier, relation):
        release = self.find_release(identifier)
        if release is None:
            return {
                "success": False,
                "message": f"Cargo Release '{identifier}' not found."
            }

        rel_dict = dict(release)
        if relation not in self.RELATIONS:
            return {
                "success": False,
                "message": f"Unknown relation '{relation}'."
            }

        config = self.RELATIONS[relation]
        records = self.fetch_relation(
            rel_dict["id"],
            config["table"],
            config["foreign_key"]
        )

        return {
            "success": True,
            "cargo_release": rel_dict,
            relation: records
        }

    ####################################################################
    # Fetch All
    ####################################################################

    def get_all(self, identifier):
        details = self.get_release_details(identifier)
        if not details.get("success"):
            return details

        release = self.find_release(identifier)
        if release is None:
            return details

        result = dict(details)
        for relation_name, config in self.RELATIONS.items():
            result[relation_name] = self.fetch_relation(
                release["id"],
                config["table"],
                config["foreign_key"]
            )

        return result

    ####################################################################
    # Unified Public Entry Point
    ####################################################################

    def fetch(self, identifier, relation="cargo_release"):
        try:
            if relation in ("cargo_release", "details", "release"):
                return self.get_release_details(identifier)
            elif relation == "all":
                return self.get_all(identifier)
            else:
                return self.get_relation(identifier, relation)
        finally:
            self.close()
