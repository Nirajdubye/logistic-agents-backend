from app.database.connection import SessionLocal
from sqlalchemy import text


class InsertTool:

    @staticmethod
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
            return {"success": False, "error": str(e)}
        finally:
            db.close()

    @staticmethod
    def insert_driver(
        employee_code,
        full_name,
        phone,
        license_number,
        status="Available",
    ):
        db = SessionLocal()
        try:
            result = db.execute(
                text("""
                    INSERT INTO drivers
                    (
                        employee_code,
                        full_name,
                        phone,
                        license_number,
                        status
                    )
                    VALUES
                    (
                        :employee_code,
                        :full_name,
                        :phone,
                        :license_number,
                        :status
                    )
                    RETURNING driver_id;
                """),
                {
                    "employee_code": employee_code,
                    "full_name": full_name,
                    "phone": phone,
                    "license_number": license_number,
                    "status": status,
                },
            )
            driver_id = result.scalar()
            db.commit()
            return {
                "success": True,
                "message": "Driver created successfully.",
                "driver_id": driver_id,
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
        finally:
            db.close()

    @staticmethod
    def insert_vehicle(
        vehicle_number,
        vehicle_type,
        capacity_tons,
        status="Available",
    ):
        db = SessionLocal()
        try:
            result = db.execute(
                text("""
                    INSERT INTO vehicles
                    (
                        vehicle_number,
                        vehicle_type,
                        capacity_tons,
                        status
                    )
                    VALUES
                    (
                        :vehicle_number,
                        :vehicle_type,
                        :capacity_tons,
                        :status
                    )
                    RETURNING vehicle_id;
                """),
                {
                    "vehicle_number": vehicle_number,
                    "vehicle_type": vehicle_type,
                    "capacity_tons": capacity_tons,
                    "status": status,
                },
            )
            vehicle_id = result.scalar()
            db.commit()
            return {
                "success": True,
                "message": "Vehicle created successfully.",
                "vehicle_id": vehicle_id,
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
        finally:
            db.close()

    @staticmethod
    def insert_shipment(
        shipment_id,
        customer_id,
        driver_id,
        vehicle_id,
        origin,
        destination,
        current_location,
        status,
        shipment_date,
        expected_delivery,
        delivered_date=None,
        weight_kg=None,
        remarks=None,
    ):
        db = SessionLocal()
        try:
            db.execute(
                text("""
                    INSERT INTO shipments
                    (
                        shipment_id,
                        customer_id,
                        driver_id,
                        vehicle_id,
                        origin,
                        destination,
                        current_location,
                        status,
                        shipment_date,
                        expected_delivery,
                        delivered_date,
                        weight_kg,
                        remarks
                    )
                    VALUES
                    (
                        :shipment_id,
                        :customer_id,
                        :driver_id,
                        :vehicle_id,
                        :origin,
                        :destination,
                        :current_location,
                        :status,
                        :shipment_date,
                        :expected_delivery,
                        :delivered_date,
                        :weight_kg,
                        :remarks
                    );
                """),
                {
                    "shipment_id": shipment_id,
                    "customer_id": customer_id,
                    "driver_id": driver_id,
                    "vehicle_id": vehicle_id,
                    "origin": origin,
                    "destination": destination,
                    "current_location": current_location,
                    "status": status,
                    "shipment_date": shipment_date,
                    "expected_delivery": expected_delivery,
                    "delivered_date": delivered_date,
                    "weight_kg": weight_kg,
                    "remarks": remarks,
                },
            )
            db.commit()
            return {
                "success": True,
                "message": "Shipment created successfully.",
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
        finally:
            db.close()

    @staticmethod
    def insert_delivery_report(
        shipment_id,
        report_date,
        delivery_status,
        delay_minutes=0,
        delivery_time_hours=0,
        remarks=None,
    ):
        db = SessionLocal()
        try:
            result = db.execute(
                text("""
                    INSERT INTO delivery_reports
                    (
                        shipment_id,
                        report_date,
                        delivery_status,
                        delay_minutes,
                        delivery_time_hours,
                        remarks
                    )
                    VALUES
                    (
                        :shipment_id,
                        :report_date,
                        :delivery_status,
                        :delay_minutes,
                        :delivery_time_hours,
                        :remarks
                    )
                    RETURNING report_id;
                """),
                {
                    "shipment_id": shipment_id,
                    "report_date": report_date,
                    "delivery_status": delivery_status,
                    "delay_minutes": delay_minutes,
                    "delivery_time_hours": delivery_time_hours,
                    "remarks": remarks,
                },
            )
            report_id = result.scalar()
            db.commit()
            return {
                "success": True,
                "message": "Delivery report created successfully.",
                "report_id": report_id,
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
        finally:
            db.close()