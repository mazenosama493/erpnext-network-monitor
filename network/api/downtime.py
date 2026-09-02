import frappe
from frappe.utils import now_datetime


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

    now = now_datetime()

    downtimes = frappe.get_all(
        "Network Downtime",
        filters=filters,
        fields=["name", "started_at"],
    )

    for downtime in downtimes:
        duration_minutes = None

        if downtime.started_at:
            duration_minutes = round(
                (now - downtime.started_at).total_seconds() / 60,
                2,
            )

        values = (
            now,
            1 if device_disabled else 0,
            1 if monitoring_down else 0,
            duration_minutes,
            now,
            frappe.session.user,
            downtime.name,
        )

        # Retry transient deadlocks
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

                break

            except frappe.QueryDeadlockError:
                if attempt == 2:
                    raise

                time.sleep(0.1 * (attempt + 1))


