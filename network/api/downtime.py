import time
import frappe
from frappe.utils import now_datetime

def close_open_downtimes(
    device=None,
    device_disabled=False,
    monitoring_down=False,
):
    filters = {
        "status": "Open",
    }

    if device:
        filters["device"] = device

    frappe.log_error(title="Monitoring Debug - Downtime", message=f"A. close_open_downtimes called with filters: {filters}")

    now = now_datetime()
    now_str = now.strftime('%Y-%m-%d %H:%M:%S')

    downtimes = frappe.get_all(
        "Network Downtime",
        filters=filters,
        fields=["name", "started_at"],
        limit_page_length=0,
    )

    frappe.log_error(title="Monitoring Debug - Downtime", message=f"B. Found {len(downtimes)} open downtimes to close.")

    if not downtimes:
        return

    success_count = 0

    for downtime in downtimes:
        duration_minutes = None

        if downtime.started_at:
            duration_minutes = round(
                (now - downtime.started_at).total_seconds() / 60,
                2,
            )

        values = (
            now_str,
            1 if device_disabled else 0,
            1 if monitoring_down else 0,
            duration_minutes,
            now_str,
            frappe.session.user,
            downtime.name,
        )

        for attempt in range(3):
            try:
                frappe.db.sql(
                    """
                    UPDATE `tabNetwork Downtime`
                    SET
                        status = 'Closed',
                        ended_at = %s,
                        device_disabled = %s,
                        monitoring_down = %s,
                        duration_minutes = %s,
                        modified = %s,
                        modified_by = %s
                    WHERE name = %s
                      AND status = 'Open'
                    """,
                    values,
                )
                success_count += 1
                break

            except frappe.QueryDeadlockError:
                frappe.log_error(title="Monitoring Debug - Downtime", message=f"Deadlock detected for downtime {downtime.name} on attempt {attempt + 1}")
                if attempt == 2:
                    raise
                time.sleep(0.1 * (attempt + 1))

    frappe.log_error(title="Monitoring Debug - Downtime", message=f"C. Successfully closed {success_count} downtimes.")