import time
import frappe

def set_status_unknown(reason, device_name=None):
    try:
        if reason == "Monitoring":
            # Use a single bulk UPDATE query with a retry block for deadlocks.
            # This avoids loading every document into memory and eliminates row-locking race conditions.
            for attempt in range(3):
                try:
                    frappe.db.sql("""
                        UPDATE `tabNetwork Device`
                        SET status = 'Unknown', modified = NOW()
                        WHERE status != 'Unknown'
                    """)
                    frappe.db.commit()
                    break
                except frappe.QueryDeadlockError:
                    frappe.db.rollback()
                    if attempt == 2:
                        raise
                    time.sleep(0.1 * (attempt + 1))

        elif reason == "Device Disabled":
            if not device_name:
                frappe.throw("Device name is required when reason is 'Device Disabled'")

            # Use frappe.db.set_value with a retry wrapper instead of heavy doc.save()
            for attempt in range(3):
                try:
                    frappe.db.set_value("Network Device", device_name, "status", "Unknown")
                    frappe.db.commit()
                    break
                except frappe.QueryDeadlockError:
                    frappe.db.rollback()
                    if attempt == 2:
                        raise
                    time.sleep(0.1 * (attempt + 1))

        return {"status": "success"}

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(
            frappe.get_traceback(),
            "Error in set_status_unknown"
        )
        return {
            "status": "error",
            "message": str(e),
        }