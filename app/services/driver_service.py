from sqlalchemy import text
from app.database.connection import SessionLocal


class DriverService:

    ####################################################################
    # Tables related with Driver/Employee
    ####################################################################

    RELATIONS = {
        "pickup_orders": {
            "table": "pickup_orders",
            "foreign_key": "employee_id"
        },
        "quotations": {
            "table": "quotations",
            "foreign_key": "employee_id"
        },
        "cargo_releases": {
            "table": "cargo_releases",
            "foreign_key": "employee_id"
        }
    }

    ####################################################################

    def __init__(self):
        self.db = SessionLocal()

    ####################################################################

    def close(self):
        self.db.close()

    ####################################################################
    # Find Driver / Employee Record
    ####################################################################

    def find_driver(self, identifier: str):
        query = text("""
            SELECT *
            FROM employees
            WHERE
                LOWER(employee_id) = LOWER(:identifier)
                OR LOWER(first_name || ' ' || last_name) = LOWER(:identifier)
                OR LOWER(first_name) = LOWER(:identifier)
                OR LOWER(last_name) = LOWER(:identifier)
                OR LOWER(email) = LOWER(:identifier)
                OR CAST(id AS TEXT) = :identifier
            LIMIT 1
        """)

        driver = self.db.execute(
            query,
            {"identifier": identifier.strip()}
        ).mappings().first()

        return driver

    ####################################################################
    # Driver Profile
    ####################################################################

    def get_driver(self, identifier: str):
        driver = self.find_driver(identifier)

        if driver is None:
            return {
                "success": False,
                "message": f"Driver/Employee '{identifier}' not found."
            }

        d = dict(driver)
        return {
            "success": True,
            "driver_id": d["employee_id"],
            "full_name": f"{d['first_name']} {d['last_name']}",
            "email": d["email"],
            "phone": d["phone_number"],
            "role": d["role"],
            "status": d["status"],
            "address": ", ".join(filter(None, [d.get("address_line_1"), d.get("city"), d.get("country")])),
            "joining_date": str(d["joining_date"]) if d.get("joining_date") else None,
            "profile": d
        }

    ####################################################################
    # Generic Relation Fetcher
    ####################################################################

    def fetch_relation(self, driver_id, table_name, foreign_key):
        query = text(f"""
            SELECT *
            FROM {table_name}
            WHERE {foreign_key} = :driver_id
        """)
        rows = self.db.execute(query, {"driver_id": driver_id}).mappings().all()
        return [dict(row) for row in rows]

    ####################################################################
    # Fetch One Relation
    ####################################################################

    def get_relation(self, identifier, relation):
        driver = self.find_driver(identifier)
        if driver is None:
            return {
                "success": False,
                "message": f"Driver/Employee '{identifier}' not found."
            }

        driver_dict = dict(driver)
        if relation not in self.RELATIONS:
            return {
                "success": False,
                "message": f"Unknown relation '{relation}'."
            }

        config = self.RELATIONS[relation]
        records = self.fetch_relation(
            driver_dict["id"],
            config["table"],
            config["foreign_key"]
        )

        return {
            "success": True,
            "driver": driver_dict,
            relation: records
        }

    ####################################################################
    # Fetch All
    ####################################################################

    def get_all(self, identifier):
        driver_details = self.get_driver(identifier)
        if not driver_details.get("success"):
            return driver_details

        driver = self.find_driver(identifier)
        if driver is None:
            return driver_details

        result = dict(driver_details)
        for relation_name, config in self.RELATIONS.items():
            result[relation_name] = self.fetch_relation(
                driver["id"],
                config["table"],
                config["foreign_key"]
            )

        return result

    ####################################################################
    # Public Entry Point
    ####################################################################

    def fetch(self, identifier, relation="driver"):
        try:
            if relation in ("driver", "profile", "details"):
                return self.get_driver(identifier)
            elif relation == "all":
                return self.get_all(identifier)
            else:
                return self.get_relation(identifier, relation)
        finally:
            self.close()
