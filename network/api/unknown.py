import time
import frappe

def set_status_unknown(reason, device_name=None):
    frappe.log_error(title="Monitoring Debug - Unknown", message=f"A. set_status_unknown called. Reason: {reason}, Device: {device_name}")
    
    try:
        if reason == "Monitoring":
            for attempt in range(3):
                try:
                    frappe.db.sql("""
                        UPDATE `tabNetwork Device`
                        SET status = 'Unknown', modified = NOW()
                        WHERE status != 'Unknown'
                    """)
                    frappe.db.commit()
                    frappe.log_error(title="Monitoring Debug - Unknown", message="B. Successfully set all devices to Unknown via SQL.")
                    break
                except frappe.QueryDeadlockError:
                    frappe.db.rollback()
                    frappe.log_error(title="Monitoring Debug - Unknown", message=f"Deadlock retry {attempt + 1} for Bulk Update.")
                    if attempt == 2:
                        raise
                    time.sleep(0.1 * (attempt + 1))

        elif reason == "Device Disabled":
            if not device_name:
                frappe.throw("Device name is required when reason is 'Device Disabled'")

            for attempt in range(3):
                try:
                    frappe.db.set_value("Network Device", device_name, "status", "Unknown")
                    frappe.db.commit()
                    frappe.log_error(title="Monitoring Debug - Unknown", message=f"B. Successfully set device {device_name} to Unknown.")
                    break
                except frappe.QueryDeadlockError:
                    frappe.db.rollback()
                    frappe.log_error(title="Monitoring Debug - Unknown", message=f"Deadlock retry {attempt + 1} for device {device_name}.")
                    if attempt == 2:
                        raise
                    time.sleep(0.1 * (attempt + 1))

        return {"status": "success"}

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(
            title="Monitoring Debug - Unknown Error",
            message=f"FAILED in set_status_unknown:\n{frappe.get_traceback()}"
        )
        return {
            "status": "error",
            "message": str(e),
        }