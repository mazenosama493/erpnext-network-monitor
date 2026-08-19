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

    now = now_datetime()

    downtimes = frappe.get_all(
        "Network Downtime",
        filters=filters,
        pluck="name",
    )

    for name in downtimes:
        doc = frappe.get_doc("Network Downtime", name)

        doc.status = "Closed"
        doc.ended_at = now

        # Mark why this downtime was closed
        doc.device_disabled = 1 if device_disabled else 0
        doc.monitoring_down = 1 if monitoring_down else 0

        if doc.started_at:
            doc.duration_minutes = round(
                (now - doc.started_at).total_seconds() / 60,
                2,
            )

        doc.save(ignore_permissions=True)



